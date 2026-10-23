[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ModelPath
)

$ErrorActionPreference = "Stop"
$tomVersion = "19.84.1"
$assemblyName = "Microsoft.AnalysisServices.Tabular.dll"
$modelDirectory = (Resolve-Path -LiteralPath $ModelPath).Path
$definitionDirectory = Join-Path $modelDirectory "definition"
if (Test-Path -LiteralPath $definitionDirectory -PathType Container) {
    $modelDirectory = (Resolve-Path -LiteralPath $definitionDirectory).Path
}
$assemblyPath = $null
$tomSource = "Power BI Desktop"

$desktopRoots = @(
    (Join-Path $env:ProgramFiles "Microsoft Power BI Desktop\bin"),
    (Join-Path ${env:ProgramFiles(x86)} "Microsoft Power BI Desktop\bin")
)
foreach ($root in $desktopRoots) {
    if (Test-Path -LiteralPath $root) {
        $installedAssembly = Get-ChildItem -LiteralPath $root -Filter $assemblyName -File -Recurse |
            Select-Object -First 1
        if ($null -ne $installedAssembly) {
            $assemblyPath = $installedAssembly.FullName
            break
        }
    }
}

if ($null -eq $assemblyPath) {
    $tomSource = "NuGet Microsoft.AnalysisServices.retail.amd64 $tomVersion"
    $packageDirectory = Join-Path $env:USERPROFILE `
        ".nuget\packages\microsoft.analysisservices.retail.amd64\$tomVersion"
    $packageFile = Join-Path $packageDirectory `
        "microsoft.analysisservices.retail.amd64.$tomVersion.nupkg"
    $extractedDirectory = Join-Path $packageDirectory "package"
    New-Item -ItemType Directory -Path $packageDirectory -Force | Out-Null

    $cachedAssembly = Get-ChildItem -LiteralPath $packageDirectory `
        -Filter $assemblyName -File -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $cachedAssembly) {
        if (-not (Test-Path -LiteralPath $packageFile)) {
            $packageUrl = "https://api.nuget.org/v3-flatcontainer/" +
                "microsoft.analysisservices.retail.amd64/$tomVersion/" +
                "microsoft.analysisservices.retail.amd64.$tomVersion.nupkg"
            & curl.exe --fail --location --silent --show-error `
                --output $packageFile $packageUrl
            if ($LASTEXITCODE -ne 0) {
                throw "NuGet download failed with exit code $LASTEXITCODE"
            }
        }
        if (-not (Test-Path -LiteralPath $extractedDirectory)) {
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            [System.IO.Compression.ZipFile]::ExtractToDirectory(
                $packageFile,
                $extractedDirectory
            )
        }
        $cachedAssembly = Get-ChildItem -LiteralPath $extractedDirectory `
            -Filter $assemblyName -File -Recurse |
            Select-Object -First 1
    }
    if ($null -eq $cachedAssembly) {
        throw "TOM assembly $assemblyName was not found in NuGet package $tomVersion"
    }
    $assemblyPath = $cachedAssembly.FullName
}

$tomAssembly = [System.Reflection.Assembly]::LoadFrom($assemblyPath)
$serializerType = $tomAssembly.GetType(
    "Microsoft.AnalysisServices.Tabular.TmdlSerializer",
    $true
)
$deserializeMethod = $serializerType.GetMethods(
    [System.Reflection.BindingFlags]::Public -bor
    [System.Reflection.BindingFlags]::Static
) |
    Where-Object {
        $parameters = $_.GetParameters()
        $_.Name -eq "DeserializeDatabaseFromFolder" -and
            $parameters.Count -eq 1 -and
            $parameters[0].ParameterType -eq [string]
    } |
    Select-Object -First 1
if ($null -eq $deserializeMethod) {
    throw "TmdlSerializer.DeserializeDatabaseFromFolder(string) was not found"
}

$database = $deserializeMethod.Invoke($null, [object[]]@($modelDirectory))
if ($null -eq $database -or $null -eq $database.Model) {
    throw "TmdlSerializer returned no database for $modelDirectory"
}
$tableCount = $database.Model.Tables.Count
if ($tableCount -eq 0) {
    throw "TmdlSerializer deserialized no model tables from $modelDirectory"
}
$assemblyVersion = [System.Reflection.AssemblyName]::GetAssemblyName(
    $assemblyPath
).Version
Write-Output "TOM assembly version: $assemblyVersion ($tomSource)"
Write-Output "TOM validation PASS: $($database.Model.Name) (tables=$tableCount)"
