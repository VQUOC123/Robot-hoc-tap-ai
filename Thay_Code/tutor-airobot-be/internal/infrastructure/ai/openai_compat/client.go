package openai_compat

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/nhanntv/tutor-airobot-be/internal/domain/service"
)

const (
	// STAGE1_PROMPT instructs the model to detect whether the image shows a student doing homework.
	STAGE1_PROMPT = `Analyze student workspace. Reply JSON only: {"doing_hw":<true/false>,"conf":<0.0-1.0>} doing_hw=true only if student is clearly doing school homework.`

	// STAGE2_PROMPT instructs the model to extract homework subject, grade, progress, and hints.
	STAGE2_PROMPT = `Student is doing homework. Reply JSON only: {"subject":"<Toán/Văn/Tiếng Anh/Lý/Hóa/Sinh/Sử/Địa/Tin/other>","grade":"<1-12 or null>","hw_type":"<bài tập/luận văn/đọc hiểu/lý thuyết/other>","progress":<0-100>,"hints":"<1-2 sentences Vietnamese hint>"}`
)

// chatRequest mirrors the OpenAI /chat/completions request body.
type chatRequest struct {
	Model     string        `json:"model"`
	MaxTokens int           `json:"max_tokens"`
	Messages  []chatMessage `json:"messages"`
}

type chatMessage struct {
	Role    string        `json:"role"`
	Content []contentPart `json:"content"`
}

type contentPart struct {
	Type     string    `json:"type"`
	Text     string    `json:"text,omitempty"`
	ImageURL *imageURL `json:"image_url,omitempty"`
}

type imageURL struct {
	URL string `json:"url"`
}

// chatResponse mirrors a minimal subset of the OpenAI /chat/completions response.
type chatResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error,omitempty"`
}

// stage1Response is the expected JSON payload from DetectHomework.
type stage1Response struct {
	DoingHW bool    `json:"doing_hw"`
	Conf    float64 `json:"conf"`
}

// stage2Response is the expected JSON payload from AnalyzeHomework.
type stage2Response struct {
	Subject string `json:"subject"`
	Grade   string `json:"grade"`
	HWType  string `json:"hw_type"`
	Progress int   `json:"progress"`
	Hints   string `json:"hints"`
}

// Ensure Client implements service.AIClient at compile time.
var _ service.AIClient = (*Client)(nil)

// Client is an OpenAI-compatible vision API client.
type Client struct {
	baseURL    string
	apiKey     string
	model      string
	httpClient *http.Client
	timeoutSec int
}

// NewClient creates a Client pointed at the given OpenAI-compatible endpoint.
func NewClient(baseURL, apiKey, model string, timeoutSec int) *Client {
	if timeoutSec <= 0 {
		timeoutSec = 30
	}
	return &Client{
		baseURL: baseURL,
		apiKey:  apiKey,
		model:   model,
		httpClient: &http.Client{
			Timeout: time.Duration(timeoutSec) * time.Second,
		},
		timeoutSec: timeoutSec,
	}
}

// visionCall sends a single-turn vision request and returns the raw text content.
func (c *Client) visionCall(ctx context.Context, imageJPEG []byte, prompt string, maxTokens int) (string, error) {
	encoded := base64.StdEncoding.EncodeToString(imageJPEG)
	dataURL := "data:image/jpeg;base64," + encoded

	body := chatRequest{
		Model:     c.model,
		MaxTokens: maxTokens,
		Messages: []chatMessage{
			{
				Role: "user",
				Content: []contentPart{
					{Type: "text", Text: prompt},
					{Type: "image_url", ImageURL: &imageURL{URL: dataURL}},
				},
			},
		},
	}

	payload, err := json.Marshal(body)
	if err != nil {
		return "", fmt.Errorf("openai_compat: marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		c.baseURL+"/chat/completions", bytes.NewReader(payload))
	if err != nil {
		return "", fmt.Errorf("openai_compat: create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.apiKey)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("openai_compat: http do: %w", err)
	}
	defer resp.Body.Close()

	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("openai_compat: read response: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return "", fmt.Errorf("openai_compat: HTTP %d: %s", resp.StatusCode, string(respBytes))
	}

	var chatResp chatResponse
	if err = json.Unmarshal(respBytes, &chatResp); err != nil {
		return "", fmt.Errorf("openai_compat: parse response: %w", err)
	}
	if chatResp.Error != nil {
		return "", fmt.Errorf("openai_compat: provider error: %s", chatResp.Error.Message)
	}
	if len(chatResp.Choices) == 0 {
		return "", fmt.Errorf("openai_compat: empty choices in response")
	}

	return chatResp.Choices[0].Message.Content, nil
}

// DetectHomework implements service.AIClient Stage 1.
func (c *Client) DetectHomework(ctx context.Context, imageJPEG []byte) (service.Stage1Result, error) {
	start := time.Now()
	raw, err := c.visionCall(ctx, imageJPEG, STAGE1_PROMPT, 80)
	if err != nil {
		return service.Stage1Result{}, fmt.Errorf("DetectHomework: %w", err)
	}
	latency := int(time.Since(start).Milliseconds())

	// Strip markdown fences if present
	raw = stripJSONFences(raw)

	var s1 stage1Response
	if err = json.Unmarshal([]byte(raw), &s1); err != nil {
		return service.Stage1Result{}, fmt.Errorf("DetectHomework: parse JSON %q: %w", raw, err)
	}

	return service.Stage1Result{
		DoingHW:    s1.DoingHW,
		Confidence: s1.Conf,
		LatencyMs:  latency,
	}, nil
}

// AnalyzeHomework implements service.AIClient Stage 2.
func (c *Client) AnalyzeHomework(ctx context.Context, imageJPEG []byte) (service.Stage2Result, error) {
	start := time.Now()
	raw, err := c.visionCall(ctx, imageJPEG, STAGE2_PROMPT, 150)
	if err != nil {
		return service.Stage2Result{}, fmt.Errorf("AnalyzeHomework: %w", err)
	}
	latency := int(time.Since(start).Milliseconds())

	raw = stripJSONFences(raw)

	var s2 stage2Response
	if err = json.Unmarshal([]byte(raw), &s2); err != nil {
		return service.Stage2Result{}, fmt.Errorf("AnalyzeHomework: parse JSON %q: %w", raw, err)
	}

	return service.Stage2Result{
		Subject:   s2.Subject,
		Grade:     s2.Grade,
		HWType:    s2.HWType,
		Progress:  s2.Progress,
		Hints:     s2.Hints,
		LatencyMs: latency,
	}, nil
}

// stripJSONFences removes ```json ... ``` markdown fences that models sometimes add.
func stripJSONFences(s string) string {
	// Trim surrounding whitespace
	for len(s) > 0 && (s[0] == ' ' || s[0] == '\n' || s[0] == '\r' || s[0] == '\t') {
		s = s[1:]
	}
	for len(s) > 0 && (s[len(s)-1] == ' ' || s[len(s)-1] == '\n' || s[len(s)-1] == '\r' || s[len(s)-1] == '\t') {
		s = s[:len(s)-1]
	}
	// Remove ```json prefix
	if len(s) >= 7 && s[:7] == "```json" {
		s = s[7:]
	} else if len(s) >= 3 && s[:3] == "```" {
		s = s[3:]
	}
	// Remove ``` suffix
	if len(s) >= 3 && s[len(s)-3:] == "```" {
		s = s[:len(s)-3]
	}
	return s
}
