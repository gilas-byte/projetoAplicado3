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
    # A paginacao do Word difere um pouco da do LibreOffice usada na montagem:
    # atualiza so os numeros de pagina, sem refazer o texto das entradas.
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
