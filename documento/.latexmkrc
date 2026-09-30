# LuaLaTeX + biber. Desde documento/: latexmk
$pdf_mode = 4;
$out_dir = 'build';
$lualatex = 'lualatex -interaction=nonstopmode -file-line-error %O %S';
@default_files = ('main.tex');
