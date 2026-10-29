# Atribuições de terceiros

## BNCC dados — bncc.dev

O inventário de pesquisa considera o projeto [bncc-dev/bncc-dados](https://github.com/bncc-dev/bncc-dados), de Profy Tecnologias Educacionais / bncc.dev. Dados: CC BY 4.0, conforme dados/LICENSE.md; código: MIT. A revisão adquirida é registrada na fonte e nos manifestos. A licença do dataset derivado não substitui a atribuição ao Ministério da Educação como emissor dos documentos da BNCC.

O processamento final deve indicar no manifesto se utilizou esse dataset ou somente os PDFs oficiais. A inclusão desta atribuição não constitui evidência de adoção ou equivalência de currículos estaduais.

## Documentos curriculares oficiais

Emissores, títulos, páginas de publicação, artefatos e condições conhecidas constam em data/manifests e nas páginas de fontes. Textos de terceiros são identificados separadamente do código MIT; consulte DATA-RIGHTS.md.

## Dependências

Versões exatas e dependências transitivas constam em package-lock.json. Inventário de licenças gerado em docs/evidence/dependency-licenses.json após a instalação final.

As versões Python são fixadas em pipeline/requirements.txt. O inventário consultado diretamente no PyPI, com versões, licenças declaradas pelo fornecedor e vulnerabilidades informadas para cada versão, está em docs/evidence/python-dependency-audit-current.json. Os pacotes instalados conservam seus próprios avisos e arquivos de licença na distribuição Python da imagem.

Pillow é usado na inspeção de linhas e colunas de imagens documentais. A versão 13.0.0 declara a licença MIT-CMU no [registro do fornecedor no PyPI](https://pypi.org/project/pillow/13.0.0/). A inspeção geométrica não altera o PDF original nem atribui significado pedagógico aos pixels.

## Processamento documental — PyMuPDF/MuPDF

O worker documental utiliza PyMuPDF, distribuído pelo fornecedor sob AGPL ou contrato comercial. Esta entrega usa o componente open source e preserva a licença em LICENSES/PyMuPDF-AGPL-3.0.txt. A licença MIT do código de autoria do projeto não relicencia o parser nem elimina as condições AGPL aplicáveis à distribuição e à disponibilização em rede.

Fontes e condições oficiais: https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright e https://github.com/pymupdf/PyMuPDF. A versão efetivamente utilizada é fixada em pipeline/requirements.txt e registrada nos manifestos de processamento; não foi comprada licença comercial. Quem hospedar uma distribuição deve disponibilizar o código correspondente e manter os avisos/licenças dos componentes, conforme seus termos. O código do projeto, scripts de build e lockfiles são entregues neste repositório.
