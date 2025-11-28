for file in *.jpg;
do
    mv "$file" "${file#PPN}"
done
