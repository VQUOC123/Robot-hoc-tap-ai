package service

import "context"

// ProcessedImage is the result of image validation and resizing.
type ProcessedImage struct {
	Data    []byte // JPEG-encoded bytes
	Width   int
	Height  int
	SizeKB  int
}

// ImageProcessor validates, resizes, and re-encodes images before AI submission.
// Implementations must handle JPEG and PNG input and always output JPEG.
type ImageProcessor interface {
	// Process validates the raw bytes, resizes to fit within maxWidth×maxHeight
	// while preserving aspect ratio, and encodes as JPEG with the given quality (1-100).
	// Returns ErrInvalidInput when the content-type is unsupported or the file is too large.
	Process(ctx context.Context, raw []byte, maxWidth, maxHeight, quality int) (ProcessedImage, error)
}
