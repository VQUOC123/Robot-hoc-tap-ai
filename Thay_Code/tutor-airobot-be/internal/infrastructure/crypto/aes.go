package crypto

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"io"
)

const nonceSize = 12 // GCM standard nonce length

// Encrypt encrypts plaintext using AES-256-GCM.
// The returned bytes are: nonce(12 bytes) || ciphertext.
// masterKeyHex must be a 64-character hex string (32 raw bytes).
func Encrypt(plaintext []byte, masterKeyHex string) ([]byte, error) {
	key, err := decodeKey(masterKeyHex)
	if err != nil {
		return nil, err
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, fmt.Errorf("crypto: create cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("crypto: create GCM: %w", err)
	}

	nonce := make([]byte, nonceSize)
	if _, err = io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, fmt.Errorf("crypto: generate nonce: %w", err)
	}

	// Seal appends ciphertext+tag to nonce
	ciphertext := gcm.Seal(nonce, nonce, plaintext, nil)
	return ciphertext, nil
}

// Decrypt decrypts AES-256-GCM ciphertext produced by Encrypt.
// Expects: nonce(12 bytes) || ciphertext.
func Decrypt(ciphertext []byte, masterKeyHex string) ([]byte, error) {
	key, err := decodeKey(masterKeyHex)
	if err != nil {
		return nil, err
	}

	if len(ciphertext) < nonceSize {
		return nil, fmt.Errorf("crypto: ciphertext too short")
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, fmt.Errorf("crypto: create cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("crypto: create GCM: %w", err)
	}

	nonce := ciphertext[:nonceSize]
	data := ciphertext[nonceSize:]

	plaintext, err := gcm.Open(nil, nonce, data, nil)
	if err != nil {
		return nil, fmt.Errorf("crypto: decrypt: %w", err)
	}
	return plaintext, nil
}

// decodeKey decodes a 64-character hex master key into 32 raw bytes.
func decodeKey(masterKeyHex string) ([]byte, error) {
	key, err := hex.DecodeString(masterKeyHex)
	if err != nil {
		return nil, fmt.Errorf("crypto: invalid master key encoding: %w", err)
	}
	if len(key) != 32 {
		return nil, fmt.Errorf("crypto: master key must be 32 bytes (64 hex chars), got %d bytes", len(key))
	}
	return key, nil
}
