die () {
  echo "$1"
  exit 1
}

python3="C:/Programmi/Python31/python.exe"

rm -rf build
mkdir build
cp -R i build/
cp -R esempi build/

echo "validating HTML"
for f in *.html; do
  "$python3" util/validate.py "$f" || die "Failed to validate $f"
done

echo "minimizing HTML"
for f in *.html; do
  "$python3" util/htmlminimizer.py "$f" build/"$f" || die "Failed to minimize $f"
done

echo "minimizing CSS"
java -jar util/yuicompressor-2.4.2.jar styles.css > build/styles.css || die "Failed to minimize CSS"

echo "inlining CSS and adding Google Analytics code"
css=`cat build/styles.css`
ga=`cat ga.js`
for f in build/*.html; do
  sed -i -e "s|<link rel=stylesheet href=styles.css>|<style>${css}</style>|g" -e "s|</style><style>||g" -e "s|</style>|</style>${ga}|g" "$f" || die "Failed to inline CSS or to add Google Analytics code"
done
rm build/styles.css