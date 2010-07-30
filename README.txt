Questa è la traduzione italiana di "Programming Scala", un libro
scritto da Dean Wampler e Alex Payne, pubblicato da O'Reilly nel
2009. La traduzione italiana, intitolata "Programmare in Scala",
è disponibile solamente all'URL:

http://gpiancastelli.altervista.org/scala-it

La traduzione del testo è completa.

La traduzione delle immagini è completa, tranne per gli screenshot
di Eclipse, IntelliJ IDEA e NetBeans, che sono stati tutti mantenuti
in inglese in quanto di quei programmi non mi è nota alcuna
localizzazione in italiano.

La traduzione degli esempi di codice inseriti nel libro è stata
compiuta deliberatamente solo per stringhe e commenti. I file
sorgenti collegati sono invece stati mantenuti nella versione
originale, compreso il percorso che corrisponde alla loro ubicazione
nell'archivio di esempi scaricabile dal sito dedicato al libro da
O'Reilly.

Nonostante il testo del libro sia stato scritto direttamente in
HTML, è necessario usare lo script publish per effettuare alcune
trasformazioni dei sorgenti (HTML, CSS, JavaScript) e infine
pubblicare in rete il risultato finale. Lo script usa i seguenti
strumenti:

- Python 3
- Java (per YUI Compressor / Google Compiler)
- vari comandi Unix come cat, sed, rm, &c.

Lo script usa anche una versione di html5lib per Python 3, che è
stata inclusa direttamente nella sottodirectory util del repository.
Tra gli altri script inclusi in util, i seguenti sono stati
riadattati da quelli usati da Mark Pilgrim per il libro "Dive Into
Python 3":

- buildtoc.py
- htmlminimizer.py
- validate.py

Tutto il materiale relativo alla traduzione è distribuito sotto
licenza CC-BY-SA 3.0. Per qualsiasi commento, scrivete una email a
<giulio.piancastelli@gmail.com>.

== MODIFICHE ==

In questa sezione, vengono riportate le modifiche effettuate nella
traduzione italiana rispetto al testo originale.

In diversi punti del libro è stato necessario correggere la scelta
del termine argomento/parametro perché spesso usati a sproposito;
saltuariamente si è voluto modificare la struttura dei paragrafi
(quasi esclusivamente incorporandone diversi in uno solo) troppo
spezzettata; e infine si è cercato di incorporare gli errata corrige
del libro segnalati sul sito dell'editore.

Si noti anche che, nelle specifiche Specs, si è deciso di usare
l'infinito dopo "should", in modo che, traducendo mentalmente la
parola inglese, si potesse leggere: "Lo scenario..." dovrebbe
"rispettare il requisito...". Come alternativa, si sarebbe potuta
usare la terza persona dell'indicativo presente, in modo che il
lettore italiano saltasse "should" e leggesse solo le stringhe che
descrivono lo scenario e il suo requisito: "Lo scenario..."
"rispetta il requisito...". Nonostante la necessità di "tradurre" i
nomi dei metodi di Specs (come appunto "should"), ho preferito
conservare l'idea di una lettura "facile" completa piuttosto che
omettere parti della specifica.

Nello specifico dei singoli capitoli, sono state apportate le
modifiche illustrate di seguito.

CH.3

"These Value methods return a Value object and they add the value to
the enumeration's collection of values."
-> Modificato, perché è la collezione di valori del *tipo
enumerato*, non l'enumerazione.

"[which] we used as the type for the argument for the isWorkingDay
method"
-> Ma in realtà è un parametro, dato che ci si riferisce alla
dichiarazione di un metodo, non a una invocazione.

CH.5

"The signature includes the type name, the list of parameters with
types, and the method's return value."
-> Ma Odersky &c., nel loro libro su Scala, dicono:
"A method's type signature comprises its name, the number, order,
and types of its parameters, if any, and its result type." (And
"Signature is short for type signature.")
(Si veda anche il Glossario, dove l'errore sulla firma del metodo si
ripete!)

"We've seen several examples of parent and child classes already."
-> Ho usato "classi basi e derivate" perché questa terminologia mi
sembra preferibile a quella "parentale" in questo breve frammento.

CH.6

"Now let's consider the second workaround we described above,
changing the declaration to var."
-> Questo in realtà è il terzo workaround.

When an instance of a class is followed by parentheses with a list
of zero or more parameters, the compiler invokes the apply method
for that instance.
-> La lista è composta di argomenti, non di parametri.

CH.7

Talvolta ho chiamato "ridefinizione" l'assegnamento di scala.<Type>
o java.lang.<Type> (in particolare, nel paragrafo che spiega il
motivo per la "ridefinizione" di java.lang.String)

Cambiata la formattazione della Tabella 7.3, usando <code> anche per
il nome dei tipi primitivi (2° colonna).

CH.8

Modificato il titolo "Traversing, Mapping, Filtering, Folding, and
Reducing" in "Operazioni comuni sulle strutture dati funzionali".

"The Scala type hierarchy for containers does have a few levels of
abstractions at the bottom, e.g., Collection extends Iterable
extends AnyRef, but above Collection are Seq (parent of List), Map,
Set, etc."
-> Ma in realtà è "at the top", perché se si immagina di seguire la
figura 7.1 List/Map/Set &c. si trovano sotto Collection, non sopra.

Aggiunto un "= &hellip;" alla firma di flatMap.

"A way to minimize this risk is to expose the lowest-level
abstractions possible."
-> Qui è esattamente il contrario: è necessario esporre le
astrazioni di livello più alto! Nel paragrafo, Iterable e Seq sono
astrazioni di livello più alto rispetto a List, perché specificano
un minor numero di dettagli!

Tolto il messaggio di errore nella sezione "Parametri di funzione
impliciti" perché confuso e incompleto.

CH.9

Non corretto: import scala.actors.Actor in alcuni esempi (e.g. Paul
Newman) non serve!

CH.11

Aggiunta una nota sulla traduzione della specifica per il DSL
interno. La nota contiene la traduzione, in modo che il lettore
possa capire il senso e/o le singole parole della specifica.

Negli ultimi due paragrafi della sezione "Un DSL esterno per il
libro paga", eliminati alcuni elementi di codice ridondanti nel
testo, quando la descrizione a parole è sufficiente. (Scelta
discutibile.)

In corsivo alcune parole mantenute in inglese (camel-case,
backtracking) nel testo.

CH.12

Modificati i tempi/riferimenti per il paragrafo della sezione
"Capire i tipi astratti" che parla dell'esempio nella sezione
"Proiezioni di tipo" perché quest'ultima segue la prima, non il
contrario come invece è stato scritto.

Nella sezione Annotazioni self-type, spostata la prima frase del
sesto paragrafo di testo alla fine del paragrafo precedente.

CH.13

Aggiunta una nota a piè di pagina sul significato di ORM.

Una considerazione sulla struttura del package encodestring è stata
resa come nota a piè di pagina.

CH.14

Aggiunta una nota su un nuovo bundle Scala per TextMate, in
sostituzione di uno citato che non esiste più.
