# ISCAS-style LaTeX manuscript

`main.tex` is the single compilation entry point. Section files live in
`sections/` and are included with `\\input`:

- `01-introduction.tex`
- `02-qac-workload.tex`
- `03-architecture.tex`
- `04-evaluation.tex`
- `05-conclusion.tex`

The manuscript uses the IEEE conference class and a BibTeX database in
`references.bib`. Build from this directory with:

```bash
make
```

The Makefile uses `latexmk` when available and otherwise falls back to the
standard `pdflatex -> bibtex -> pdflatex -> pdflatex` sequence. Replace the
placeholder author block and bracketed result fields before submission.

## VS Code 自动编译

推荐安装 `James-Yu.latex-workshop` 扩展，然后用 VS Code 打开整个工程或
`paper/tex` 文件夹。对应的 `.vscode/settings.json` 已配置为：保存
`main.tex` 或 `sections/*.tex` 后自动执行本目录的 `make`，并在编辑器中
刷新生成的 PDF。第一次打开工程时，VS Code 会根据
`.vscode/extensions.json` 提示安装扩展。

如果自动编译没有触发，请确认打开的是工程文件夹，而不是单独打开某个
`.tex` 文件；也可以在命令面板执行
`LaTeX Workshop: Build LaTeX project` 手动触发一次。

The hardware setup distinguishes measured 28-nm DC results from 7-nm
technology-normalized estimates. Block-only cycle-model scope and excluded
T5/VAE/scheduler work are stated explicitly in the Experimental Setup.
