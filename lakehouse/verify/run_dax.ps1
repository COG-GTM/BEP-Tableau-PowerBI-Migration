param(
    [Parameter(Mandatory = $true)][string]$Dir,
    [Parameter(Mandatory = $true)][int]$Port,
    [Parameter(Mandatory = $false)][string]$Filter = "*.dax"
)

$clientPath = "C:\Program Files\Microsoft Power BI Desktop\bin\Microsoft.PowerBI.AdomdClient.dll"
if (-not (Test-Path $clientPath)) {
    throw "Power BI ADOMD client was not found at $clientPath"
}
Add-Type -Path $clientPath
$connection = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection(
    "Data Source=localhost:$Port"
)
$connection.Open()
$invariant = [Globalization.CultureInfo]::InvariantCulture
$escapeCsv = {
    param($value)
    if ($value -match '[",\r\n]') {
        '"' + ($value -replace '"', '""') + '"'
    }
    else {
        $value
    }
}

try {
    foreach ($file in Get-ChildItem $Dir -Filter $Filter | Sort-Object Name) {
        $command = $connection.CreateCommand()
        $command.CommandText = [IO.File]::ReadAllText($file.FullName)
        $command.CommandTimeout = 600
        $adapter = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdDataAdapter($command)
        $table = New-Object System.Data.DataTable
        try {
            [void]$adapter.Fill($table)
        }
        catch {
            $message = "$($file.Name): $($_.Exception.InnerException.Message) $($_.Exception.Message)"
            [Console]::Error.WriteLine($message)
            exit 1
        }

        $path = [IO.Path]::ChangeExtension($file.FullName, ".csv")
        $writer = New-Object IO.StreamWriter(
            $path,
            $false,
            (New-Object Text.UTF8Encoding($false))
        )
        try {
            $headers = foreach ($column in $table.Columns) {
                & $escapeCsv $column.ColumnName
            }
            $writer.WriteLine(($headers -join ","))
            foreach ($row in $table.Rows) {
                $values = foreach ($column in $table.Columns) {
                    $value = $row[$column]
                    if ($value -is [DBNull]) {
                        ""
                    }
                    elseif ($value -is [datetime]) {
                        & $escapeCsv $value.ToString("yyyy-MM-dd HH:mm:ss", $invariant)
                    }
                    elseif ($value -is [double] -or $value -is [decimal] -or $value -is [single]) {
                        & $escapeCsv $value.ToString("R", $invariant)
                    }
                    else {
                        & $escapeCsv ([Convert]::ToString($value, $invariant))
                    }
                }
                $writer.WriteLine(($values -join ","))
            }
        }
        finally {
            $writer.Dispose()
        }
        $command.Dispose()
        $adapter.Dispose()
        $table.Dispose()
    }
}
finally {
    $connection.Close()
    $connection.Dispose()
}
