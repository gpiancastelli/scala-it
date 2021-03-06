import codecs
import re
import types
import sys

from .constants import EOF, spaceCharacters, asciiLetters, asciiUppercase
from .constants import encodings, ReparseException

#Non-unicode versions of constants for use in the pre-parser
spaceCharactersBytes = [str(item) for item in spaceCharacters]
asciiLettersBytes = [str(item) for item in asciiLetters]
asciiUppercaseBytes = [str(item) for item in asciiUppercase]

invalid_unicode_re = re.compile("[\u0001-\u0008\u000B\u000E-\u001F\u007F-\u009F\uD800-\uDFFF\uFDD0-\uFDDF\uFFFE\uFFFF\U0001FFFE\U0001FFFF\U0002FFFE\U0002FFFF\U0003FFFE\U0003FFFF\U0004FFFE\U0004FFFF\U0005FFFE\U0005FFFF\U0006FFFE\U0006FFFF\U0007FFFE\U0007FFFF\U0008FFFE\U0008FFFF\U0009FFFE\U0009FFFF\U000AFFFE\U000AFFFF\U000BFFFE\U000BFFFF\U000CFFFE\U000CFFFF\U000DFFFE\U000DFFFF\U000EFFFE\U000EFFFF\U000FFFFE\U000FFFFF\U0010FFFE\U0010FFFF]")

ascii_punctuation_re = re.compile(r"[\u0009-\u000D\u0020-\u002F\u003A-\u0040\u005B-\u0060\u007B-\u007E]")

# Cache for charsUntil()
charsUntilRegEx = {}
        
class BufferedStream:
    """Buffering for streams that do not have buffering of their own

    The buffer is implemented as a list of chunks on the assumption that 
    joining many strings will be slow since it is O(n**2)
    """
    
    def __init__(self, stream):
        self.stream = stream
        self.buffer = []
        self.position = [-1,0] #chunk number, offset

    def tell(self):
        pos = 0
        for chunk in self.buffer[:self.position[0]]:
            pos += len(chunk)
        pos += self.position[1]
        return pos

    def seek(self, pos):
        assert pos < self._bufferedBytes()
        offset = pos
        i = 0
        while len(self.buffer[i]) < offset:
            offset -= pos
            i += 1
        self.position = [i, offset]

    def read(self, bytes):
        if not self.buffer:
            return self._readStream(bytes)
        elif (self.position[0] == len(self.buffer) and
              self.position[1] == len(self.buffer[-1])):
            return self._readStream(bytes)
        else:
            return self._readFromBuffer(bytes)
    
    def _bufferedBytes(self):
        return sum([len(item) for item in self.buffer])

    def _readStream(self, bytes):
        data = self.stream.read(bytes)
        self.buffer.append(data)
        self.position[0] += 1
        self.position[1] = len(data)
        return data

    def _readFromBuffer(self, bytes):
        remainingBytes = bytes
        rv = []
        bufferIndex = self.position[0]
        bufferOffset = self.position[1]
        while bufferIndex < len(self.buffer) and remainingBytes != 0:
            assert remainingBytes > 0
            bufferedData = self.buffer[bufferIndex]
            
            if remainingBytes <= len(bufferedData) - bufferOffset:
                bytesToRead = remainingBytes
                self.position = [bufferIndex, bufferOffset + bytesToRead]
            else:
                bytesToRead = len(bufferedData) - bufferOffset
                self.position = [bufferIndex, len(bufferedData)]
                bufferIndex += 1
            data = rv.append(bufferedData[bufferOffset: 
                                          bufferOffset + bytesToRead])
            remainingBytes -= bytesToRead

            bufferOffset = 0

        if remainingBytes:
            rv.append(self._readStream(remainingBytes))
        
        return "".join(rv)
        


class HTMLInputStream:
    """Provides a unicode stream of characters to the HTMLTokenizer.

    This class takes care of character encoding and removing or replacing
    incorrect byte-sequences and also provides column and line tracking.

    """

    _defaultChunkSize = 10240

    def __init__(self, source, encoding=None, parseMeta=True, chardet=True):
        """Initialises the HTMLInputStream.

        HTMLInputStream(source, [encoding]) -> Normalized stream from source
        for use by html5lib.

        source can be either a file-object, local filename or a string.

        The optional encoding parameter must be a string that indicates
        the encoding.  If specified, that encoding will be used,
        regardless of any BOM or later declaration (such as in a meta
        element)
        
        parseMeta - Look for a <meta> element containing encoding information

        """
        # List of where new lines occur
        self.newLines = [0]

        self.charEncoding = (codecName(encoding), "certain")

        # Raw Stream - for string objects this will encode to utf-8 and set
        #              self.charEncoding as appropriate
        self.rawStream = self.openStream(source)

        # Encoding Information
        #Number of bytes to use when looking for a meta element with
        #encoding information
        self.numBytesMeta = 512
        #Number of bytes to use when using detecting encoding using chardet
        self.numBytesChardet = 100
        #Encoding to use if no other information can be found
        self.defaultEncoding = "windows-1252"
        
        #Detect encoding iff no explicit "transport level" encoding is supplied
        if (self.charEncoding[0] is None):
            self.charEncoding = self.detectEncoding(parseMeta, chardet)

        self.reset()

    def reset(self):
        self.dataStream = codecs.getreader(self.charEncoding[0])(self.rawStream,
                                                                 'replace')

        self.chunk = ""
        self.chunkSize = 0
        self.chunkOffset = 0
        self.errors = []

        # Remember the current position in the document
        self.positionLine = 1
        self.positionCol = 0
        # Remember the length of the last line, so unget("\n") can restore
        # positionCol. (Only one character can be ungot at once, so we only
        # need to remember the single last line.)
        self.lastLineLength = None
        
        #Flag to indicate we may have a CR LF broken across a data chunk
        self._lastChunkEndsWithCR = False

    def openStream(self, source):
        """Produces a file object from source.

        source can be either a file object, local filename or a string.

        """
        # Already a file object
        if hasattr(source, 'read'):
            #This is wrong. We need a generic way to tell the difference 
            #between file-like objects that produce strings and those that 
            #produce bytes. We also need a good way to deal with the ones 
            #that produce strings, in particular getting the replacement 
            #characters right.
            if not hasattr(source, 'encoding'):
                stream = source
            else:
                raise NotImplementedError("Files not opened in binary mode not yet supported")
        else:
            # Otherwise treat source as a string and convert to a file object
            if isinstance(source, str):
                source = source.encode('utf-8')
                self.charEncoding = ("utf-8", "certain")
            import io
            stream = io.BytesIO(bytes(source))

        if (not(hasattr(stream, "tell") and hasattr(stream, "seek")) or
            stream is sys.stdin):
            stream = BufferedStream(stream)

        return stream

    def detectEncoding(self, parseMeta=True, chardet=True):

        #First look for a BOM
        #This will also read past the BOM if present
        encoding = self.detectBOM()
        confidence = "certain"
        #If there is no BOM need to look for meta elements with encoding 
        #information
        if encoding is None and parseMeta:
            encoding = self.detectEncodingMeta()
            confidence = "tentative"
        #Guess with chardet, if avaliable
        if encoding is None and chardet:
            confidence = "tentative"
            try:
                from chardet.universaldetector import UniversalDetector
                buffers = []
                detector = UniversalDetector()
                while not detector.done:
                    buffer = self.rawStream.read(self.numBytesChardet)
                    if not buffer:
                        break
                    buffers.append(buffer)
                    detector.feed(buffer)
                detector.close()
                encoding = detector.result['encoding']
                self.rawStream.seek(0)
            except ImportError:
                pass
        # If all else fails use the default encoding
        if encoding is None:
            confidence="tentative"
            encoding = self.defaultEncoding
        
        #Substitute for equivalent encodings:
        encodingSub = {"iso-8859-1":"windows-1252"}

        if encoding.lower() in encodingSub:
            encoding = encodingSub[encoding.lower()]

        return encoding, confidence

    def changeEncoding(self, newEncoding):
        newEncoding = codecName(newEncoding)
        if newEncoding in ("utf-16", "utf-16-be", "utf-16-le"):
            newEncoding = "utf-8"
        if newEncoding is None:
            return
        elif newEncoding == self.charEncoding[0]:
            self.charEncoding = (self.charEncoding[0], "certian")
        else:
            self.rawStream.seek(0)
            self.reset()
            self.charEncoding = (newEncoding, "certian")
            raise ReparseException("Encoding changed from %s to %s"%(self.charEncoding[0], newEncoding))
            
    def detectBOM(self):
        """Attempts to detect at BOM at the start of the stream. If
        an encoding can be determined from the BOM return the name of the
        encoding otherwise return None"""
        bomDict = {
            codecs.BOM_UTF8: 'utf-8', 
            codecs.BOM_UTF16_LE: 'utf-16-le',
            codecs.BOM_UTF16_BE: 'utf-16-be',
            codecs.BOM_UTF32_LE: 'utf-32-le',
            codecs.BOM_UTF32_BE: 'utf-32-be'
        }

        # Go to beginning of file and read in 4 bytes
        string = self.rawStream.read(4)

        # Try detecting the BOM using bytes from the string
        encoding = bomDict.get(string[:3])         # UTF-8
        seek = 3
        if not encoding:
            # Need to detect UTF-32 before UTF-16
            encoding = bomDict.get(string)         # UTF-32
            seek = 4
            if not encoding:
                encoding = bomDict.get(string[:2]) # UTF-16
                seek = 2

        # Set the read position past the BOM if one was found, otherwise
        # set it to the start of the stream
        self.rawStream.seek(encoding and seek or 0)

        return encoding

    def detectEncodingMeta(self):
        """Report the encoding declared by the meta element
        """
        buffer = self.rawStream.read(self.numBytesMeta)
        parser = EncodingParser(buffer)
        self.rawStream.seek(0)
        encoding = parser.getEncoding()
        
        if encoding in ("utf-16", "utf-16-be", "utf-16-le"):
            encoding = "utf-8"

        return encoding

    def updatePosition(self, chars):
        # Update the position attributes to correspond to some sequence of
        # read characters

        # Find the last newline character
        idx = chars.rfind("\n")
        if idx == -1:
            # No newlines in chars
            self.positionCol += len(chars)
        else:
            # Find the last-but-one newline character
            idx2 = chars.rfind("\n", 0, idx)
            if idx2 == -1:
                # Only one newline in chars
                self.positionLine += 1
                self.lastLineLength = self.positionCol + idx
                self.positionCol = len(chars) - (idx + 1)
            else:
                # At least two newlines in chars
                newlines = chars.count("\n")
                self.positionLine += newlines
                self.lastLineLength = idx - (idx2 + 1)
                self.positionCol = len(chars) - (idx + 1)

    def position(self):
        """Returns (line, col) of the current position in the stream."""
        return (self.positionLine, self.positionCol)

    def char(self):
        """ Read one character from the stream or queue if available. Return
            EOF when EOF is reached.
        """
        # Read a new chunk from the input stream if necessary
        if self.chunkOffset >= self.chunkSize:
            if not self.readChunk():
                return EOF

        char = self.chunk[self.chunkOffset]
        self.chunkOffset += 1

        # Update the position attributes
        if char == "\n":
            self.lastLineLength = self.positionCol
            self.positionCol = 0
            self.positionLine += 1
        elif char is not EOF:
            self.positionCol += 1

        return char

    def readChunk(self, chunkSize=_defaultChunkSize):
        self.chunk = ""
        self.chunkSize = 0
        self.chunkOffset = 0

        data = self.dataStream.read(chunkSize)

        if not data:
            return False
        #Replace null characters
        for i in range(data.count("\u0000")):
            self.errors.append("null-character")
        for i in range(len(invalid_unicode_re.findall(data))):
            self.errors.append("invalid-codepoint")

        data = data.replace("\u0000", "\ufffd")
        #Check for CR LF broken across chunks
        if (self._lastChunkEndsWithCR and data[0] == "\n"):
            data = data[1:]
            # Stop if the chunk is now empty
            if not data:
                return False
        self._lastChunkEndsWithCR = data[-1] == "\r"
        data = data.replace("\r\n", "\n")
        data = data.replace("\r", "\n")

        self.chunk = data
        self.chunkSize = len(data)

        return True

    def charsUntil(self, characters, opposite = False):
        """ Returns a string of characters from the stream up to but not
        including any character in 'characters' or EOF. 'characters' must be
        a container that supports the 'in' method and iteration over its
        characters.
        """

        # Use a cache of regexps to find the required characters
        try:
            chars = charsUntilRegEx[(characters, opposite)]
        except KeyError:
            for c in characters: assert(ord(c) < 128)
            regex = "".join(["\\x%02x" % ord(c) for c in characters])
            if not opposite:
                regex = "^%s" % regex
            chars = charsUntilRegEx[(characters, opposite)] = re.compile("[%s]+" % regex)

        rv = []

        while True:
            # Find the longest matching prefix
            m = chars.match(self.chunk, self.chunkOffset)
            if m is None:
                # If nothing matched, and it wasn't because we ran out of chunk,
                # then stop
                if self.chunkOffset != self.chunkSize:
                    break
            else:
                end = m.end()
                # If not the whole chunk matched, return everything
                # up to the part that didn't match
                if end != self.chunkSize:
                    rv.append(self.chunk[self.chunkOffset:end])
                    self.chunkOffset = end
                    break
            # If the whole remainder of the chunk matched,
            # use it all and read the next chunk
            rv.append(self.chunk[self.chunkOffset:])
            if not self.readChunk():
                # Reached EOF
                break

        r = "".join(rv)
        self.updatePosition(r)
        return r

    def unget(self, char):
        # Only one character is allowed to be ungotten at once - it must
        # be consumed again before any further call to unget

        if char is not None:
            if self.chunkOffset == 0:
                # unget is called quite rarely, so it's a good idea to do
                # more work here if it saves a bit of work in the frequently
                # called char and charsUntil.
                # So, just prepend the ungotten character onto the current
                # chunk:
                self.chunk = char + self.chunk
                self.chunkSize += 1
            else:
                self.chunkOffset -= 1
                assert self.chunk[self.chunkOffset] == char

            # Update the position attributes
            if char == "\n":
                assert self.positionLine >= 1
                assert self.lastLineLength is not None
                self.positionLine -= 1
                self.positionCol = self.lastLineLength
                self.lastLineLength = None
            else:
                self.positionCol -= 1

class EncodingBytes(bytes):
    """Bytes-like object with an assosiated position and various extra methods
    If the position is ever greater than the string length then an exception is
    raised"""
    def __new__(self, value):
        return bytes.__new__(self, value)

    def __init__(self, value):
        self._position = -1
    
    def __iter__(self):
        return self
    
    def __next__(self):
        self._position += 1
        rv = self[self.position]
        return rv
    
    def setPosition(self, position):
        if self._position >= len(self):
            raise StopIteration
        self._position = position
    
    def getPosition(self):
        if self._position >= len(self):
            raise StopIteration
        if self._position >= 0:
            return self._position
        else:
            return None
    
    position = property(getPosition, setPosition)

    def getCurrentByte(self):
        return self[self.position]
    
    currentByte = property(getCurrentByte)

    def skip(self, chars=spaceCharactersBytes):
        """Skip past a list of characters"""
        while self.currentByte in chars:
            self.position += 1

    def matchBytes(self, bytes, lower=False):
        """Look for a sequence of bytes at the start of a string. If the bytes 
        are found return True and advance the position to the byte after the 
        match. Otherwise return False and leave the position alone"""
        data = self[self.position:self.position+len(bytes)]
        if lower:
            data = data.lower()
        rv = data.startswith(bytes)
        if rv == True:
            self.position += len(bytes)
        return rv
    
    def jumpTo(self, bytes):
        """Look for the next sequence of bytes matching a given sequence. If
        a match is found advance the position to the last byte of the match"""
        newPosition = self[self.position:].find(bytes)
        if newPosition > -1:
            self._position += (newPosition + len(bytes)-1)
            return True
        else:
            raise StopIteration
    
    def findNext(self, byteList):
        """Move the pointer so it points to the next byte in a set of possible
        bytes"""
        while (self.currentByte not in byteList):
            self.position += 1

class EncodingParser(object):
    """Mini parser for detecting character encoding from meta elements"""

    def __init__(self, data):
        """data - the data to work on for encoding detection"""
        self.data = EncodingBytes(data)
        self.encoding = None

    def getEncoding(self):
        methodDispatch = (
            (b"<!--",self.handleComment),
            (b"<meta",self.handleMeta),
            (b"</",self.handlePossibleEndTag),
            (b"<!",self.handleOther),
            (b"<?",self.handleOther),
            (b"<",self.handlePossibleStartTag))
        for byte in self.data:
            keepParsing = True
            for key, method in methodDispatch:
                if self.data.matchBytes(key, lower=True):
                    try:
                        keepParsing = method()    
                        break
                    except StopIteration:
                        keepParsing=False
                        break
            if not keepParsing:
                break
        
        return self.encoding

    def handleComment(self):
        """Skip over comments"""
        return self.data.jumpTo(b"-->")

    def handleMeta(self):
        if self.data.currentByte not in spaceCharactersBytes:
            #if we have <meta not followed by a space so just keep going
            return True
        #We have a valid meta element we want to search for attributes
        while True:
            #Try to find the next attribute after the current position
            attr = self.getAttribute()
            if attr is None:
                return True
            else:
                if attr[0] == b"charset":
                    tentativeEncoding = attr[1]
                    codec = codecName(tentativeEncoding)
                    if codec is not None:
                        self.encoding = codec
                        return False
                elif attr[0] == b"content":
                    contentParser = ContentAttrParser(EncodingBytes(attr[1]))
                    tentativeEncoding = contentParser.parse()
                    codec = codecName(tentativeEncoding)
                    if codec is not None:
                        self.encoding = codec
                        return False

    def handlePossibleStartTag(self):
        return self.handlePossibleTag(False)

    def handlePossibleEndTag(self):
        self.data.position+=1
        return self.handlePossibleTag(True)

    def handlePossibleTag(self, endTag):
        if self.data.currentByte not in asciiLettersBytes:
            #If the next byte is not an ascii letter either ignore this
            #fragment (possible start tag case) or treat it according to 
            #handleOther
            if endTag:
                self.data.position -= 1
                self.handleOther()
            return True
        
        self.data.findNext(list(spaceCharactersBytes) + [b"<", b">"])
        if self.data.currentByte == b"<":
            #return to the first step in the overall "two step" algorithm
            #reprocessing the < byte
            self.data.position -= 1    
        else:
            #Read all attributes
            attr = self.getAttribute()
            while attr is not None:
                attr = self.getAttribute()
        return True

    def handleOther(self):
        return self.data.jumpTo(b">")

    def getAttribute(self):
        """Return a name,value pair for the next attribute in the stream, 
        if one is found, or None"""
        self.data.skip(list(spaceCharactersBytes)+[b"/"])
        if self.data.currentByte == b"<":
            self.data.position -= 1
            return None
        elif self.data.currentByte == b">":
            return None
        attrName = []
        attrValue = []
        spaceFound = False
        #Step 5 attribute name
        while True:
            if self.data.currentByte == b"=" and attrName:   
                break
            elif self.data.currentByte in spaceCharactersBytes:
                spaceFound=True
                break
            elif self.data.currentByte in (b"/", b"<", b">"):
                return b"".join(attrName), ""
            elif self.data.currentByte in asciiUppercaseBytes:
                attrName.extend(self.data.currentByte.lower())
            else:
                attrName.extend(self.data.currentByte)
            #Step 6
            self.data.position += 1
        #Step 7
        if spaceFound:
            self.data.skip()
            #Step 8
            if self.data.currentByte != b"=":
                self.data.position -= 1
                return b"".join(attrName), b""
        #XXX need to advance position in both spaces and value case
        #Step 9
        self.data.position += 1
        #Step 10
        self.data.skip()
        #Step 11
        if self.data.currentByte in (b"'", b'"'):
            #11.1
            quoteChar = self.data.currentByte
            while True:
                self.data.position+=1
                #11.3
                if self.data.currentByte == quoteChar:
                    self.data.position += 1
                    return "".join(attrName), "".join(attrValue)
                #11.4
                elif self.data.currentByte in asciiUppercaseBytes:
                    attrValue.extend(self.data.currentByte.lower())
                #11.5
                else:
                    attrValue.extend(self.data.currentByte)
        elif self.data.currentByte in (b">", b"<"):
                return b"".join(attrName), b""
        elif self.data.currentByte in asciiUppercaseBytes:
            attrValue.extend(self.data.currentByte.lower())
        else:
            attrValue.extend(self.data.currentByte)
        while True:
            self.data.position +=1
            if self.data.currentByte in (
                list(spaceCharactersBytes) + [b">", b"<"]):
                return b"".join(attrName), "".join(attrValue)
            elif self.data.currentByte in asciiUppercaseBytes:
                attrValue.extend(self.data.currentByte.lower())
            else:
                attrValue.extend(self.data.currentByte)


class ContentAttrParser(object):
    def __init__(self, data):
        self.data = data
    def parse(self):
        try:
            #Skip to the first ";"
            self.data.jumpTo(b";")
            self.data.position += 1
            self.data.skip()
            #Check if the attr name is charset 
            #otherwise return
            self.data.jumpTo(b"charset")
            self.data.position += 1
            self.data.skip()
            if not self.data.currentByte == b"=":
                #If there is no = sign keep looking for attrs
                return None
            self.data.position += 1
            self.data.skip()
            #Look for an encoding between matching quote marks
            if self.data.currentByte in (b'"', b"'"):
                quoteMark = self.data.currentByte
                self.data.position += 1
                oldPosition = self.data.position
                self.data.jumpTo(quoteMark)
                return self.data[oldPosition:self.data.position]
            else:
                #Unquoted value
                oldPosition = self.data.position
                try:
                    self.data.findNext(spaceCharactersBytes)
                    return self.data[oldPosition:self.data.position]
                except StopIteration:
                    #Return the whole remaining value
                    return self.data[oldPosition:]
        except StopIteration:
            return None


def codecName(encoding):
    """Return the python codec name corresponding to an encoding or None if the
    string doesn't correspond to a valid encoding."""
    if type(encoding) == bytes:
        encoding = str(encoding, "ascii")
    if (encoding is not None) and (type(encoding) == str):
        canonicalName = ascii_punctuation_re.sub("", encoding).lower()
        return encodings.get(canonicalName, None)
    else:
        return None
