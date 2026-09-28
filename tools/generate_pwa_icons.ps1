Add-Type -AssemblyName System.Drawing

$projectRoot = Split-Path -Parent $PSScriptRoot
$sourcePath = Join-Path $projectRoot 'static\images\logo-ma.png'
$targetDir = Join-Path $projectRoot 'static\pwa'
$source = [System.Drawing.Image]::FromFile($sourcePath)

try {
    foreach ($icon in @(
        @{ Name = 'icon-192.png'; Size = 192; Scale = 0.78 },
        @{ Name = 'icon-512.png'; Size = 512; Scale = 0.78 },
        @{ Name = 'icon-maskable-512.png'; Size = 512; Scale = 0.62 }
    )) {
        $size = [int]$icon.Size
        $bitmap = [System.Drawing.Bitmap]::new($size, $size)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $attributes = [System.Drawing.Imaging.ImageAttributes]::new()
        try {
            $graphics.Clear([System.Drawing.Color]::FromArgb(248, 245, 239))
            $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
            $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

            $matrix = [System.Drawing.Imaging.ColorMatrix]::new()
            $matrix.Matrix00 = 0
            $matrix.Matrix11 = 0
            $matrix.Matrix22 = 0
            $matrix.Matrix40 = 25 / 255
            $matrix.Matrix41 = 60 / 255
            $matrix.Matrix42 = 44 / 255
            $attributes.SetColorMatrix($matrix)

            $height = [int][Math]::Round($size * $icon.Scale)
            $width = [int][Math]::Round($height * $source.Width / $source.Height)
            $destination = [System.Drawing.Rectangle]::new(
                [int](($size - $width) / 2), [int](($size - $height) / 2), $width, $height
            )
            $graphics.DrawImage($source, $destination, 0, 0, $source.Width, $source.Height,
                [System.Drawing.GraphicsUnit]::Pixel, $attributes)
            $bitmap.Save((Join-Path $targetDir $icon.Name), [System.Drawing.Imaging.ImageFormat]::Png)
        }
        finally {
            $attributes.Dispose()
            $graphics.Dispose()
            $bitmap.Dispose()
        }
    }
}
finally {
    $source.Dispose()
}
