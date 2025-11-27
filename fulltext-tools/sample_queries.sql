-- get all pages, ppns and thumbnail paths for a given word
SELECT DISTINCT wp.rel_number,wp.rel_ppn,p.path FROM word_pages wp INNER JOIN pages p ON rel_number=p."number" AND wp.rel_ppn=p.rel_ppn WHERE rel_word LIKE 'Gast';
