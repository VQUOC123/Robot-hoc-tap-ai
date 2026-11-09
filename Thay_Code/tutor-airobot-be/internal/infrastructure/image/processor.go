package image

import (
	"bytes"
	"context"
	"fmt"
	"image/jpeg"
	"image/png"
	"net/http"

	"github.com/disintegration/imaging"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/apperror"
	"github.com/nhanntv/tutor-airobot-be/internal/domain/service"
)

const defaultMaxRawSizeMB = 10

// Processor implements service.ImageProcessor using the imaging library.
type Processor struct {
	maxRawSizeMB int
}

// NewProcessor creates a Processor with the given raw-input size cap in megabytes.
func NewProcessor(maxRawSizeMB int) *Processor {
	if maxRawSizeMB <= 0 {
		maxRawSizeMB = defaultMaxRawSizeMB
	}
	return &Processor{maxRawSizeMB: maxRawSizeMB}
}

// Ensure Processor implements service.ImageProcessor at compile time.
var _ service.ImageProcessor = (*Processor)(nil)

// Process validates, resizes, and re-encodes the raw image bytes as JPEG.
func (p *Processor) Process(_ context.Context, raw []byte, maxWidth, maxHeight, quality int) (service.ProcessedImage, error) {
	limitBytes := p.maxRawSizeMB * 1024 * 1024
	if len(raw) > limitBytes {
		return service.ProcessedImage{}, apperror.InvalidInput(
			fmt.Sprintf("image exceeds maximum size of %d MB", p.maxRawSizeMB),
		)
	}

	// Detect content type from first 512 bytes
	ct := http.DetectContentType(raw)
	if ct != "image/jpeg" && ct != "image/png" {
		return service.ProcessedImage{}, apperror.InvalidInput(
			fmt.Sprintf("unsupported image type %q: only JPEG and PNG are accepted", ct),
		)
	}

	// Validate that the bytes decode cleanly before resizing
	reader := bytes.NewReader(raw)
	switch ct {
	case "image/jpeg":
		if _, err := jpeg.DecodeConfig(reader); err != nil {
			return service.ProcessedImage{}, apperror.InvalidInput("JPEG decode failed: " + err.Error())
		}
	case "image/png":
		if _, err := png.DecodeConfig(reader); err != nil {
			return service.ProcessedImage{}, apperror.InvalidInput("PNG decode failed: " + err.Error())
		}
	}

	// Use imaging for type-safe resize — it re-decodes internally
	src, err := imaging.Decode(bytes.NewReader(raw))
	if err != nil {
		return service.ProcessedImage{}, apperror.InvalidInput("image decode failed: " + err.Error())
	}

	// Clamp dimensions
	if maxWidth <= 0 {
		maxWidth = 1024
	}
	if maxHeight <= 0 {
		maxHeight = 768
	}
	if quality <= 0 || quality > 100 {
		quality = 82
	}

	// Fit preserves aspect ratio — never upscales
	resized := imaging.Fit(src, maxWidth, maxHeight, imaging.Lanczos)

	bounds := resized.Bounds()
	w := bounds.Max.X - bounds.Min.X
	h := bounds.Max.Y - bounds.Min.Y

	// Encode as JPEG
	var buf bytes.Buffer
	if err = jpeg.Encode(&buf, resized, &jpeg.Options{Quality: quality}); err != nil {
		return service.ProcessedImage{}, fmt.Errorf("image encode: %w", err)
	}

	data := buf.Bytes()
	sizeKB := (len(data) + 1023) / 1024

	return service.ProcessedImage{
		Data:   data,
		Width:  w,
		Height: h,
		SizeKB: sizeKB,
	}, nil
}
