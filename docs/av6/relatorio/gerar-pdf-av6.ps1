# Gera o PDF da AV6 no Word a partir do .docx, com os numeros de pagina do sumario
# atualizados. Rodar na raiz do clone, com o Word fechado:
#   powershell -ExecutionPolicy Bypass -File docs\av6\relatorio\gerar-pdf-av6.ps1
$ErrorActionPreference = "Stop"
$docx = (Resolve-Path "docs\av6\AV6_Relatorio_Final_RadarENEM_EquipeA.docx").Path
$pdf  = $docx -replace '\.docx$', '.pdf'

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($docx)
    $doc.Repaginate()
    # Refaz o sumario inteiro no Word (entradas no formato dos titulos, como no
    # "Atualizar o indice inteiro"), repagina e confere de novo os numeros de pagina,
    # porque a paginacao do Word difere um pouco da do LibreOffice usada na montagem.
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Repaginate()
    foreach ($toc in $doc.TablesOfContents) { $toc.UpdatePageNumbers() }
    $doc.Save()
    $doc.ExportAsFixedFormat($pdf, 17)   # 17 = PDF
    $paginas = $doc.ComputeStatistics(2) # 2 = paginas
    $doc.Close()
    Write-Host "PDF gerado: $pdf ($paginas paginas)"
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
