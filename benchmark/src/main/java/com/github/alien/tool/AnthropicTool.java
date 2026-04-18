package com.github.alien.tool;

import java.util.stream.Collectors;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.errors.InternalServerException;
import com.anthropic.errors.RateLimitException;
import com.anthropic.models.messages.Message;
import com.anthropic.models.messages.MessageCreateParams;
import com.anthropic.models.messages.Model;
import com.anthropic.models.messages.OutputConfig;
import com.anthropic.models.messages.ThinkingConfigAdaptive;
import com.anthropic.models.messages.ThinkingConfigEnabled;


public class AnthropicTool extends LLMTool {
    private static final AnthropicClient ANTHROPIC = AnthropicOkHttpClient.builder()
        .apiKey(dotenv.get("ANTHROPIC_API_KEY"))
        .build();
    private static final String RETRY_HEADER = "retry-after";
    private static final String DEFAULT_RETRY = "1"; 
    private static final Model MODEL = Model.CLAUDE_OPUS_4_6;

    @Override
    public String getName() {
        return "claude-opus-4.6";
    }

    @Override
    protected String askModel(String systemPrompt, String userPrompt) {
        MessageCreateParams params = buildParams(systemPrompt, userPrompt);
        return askModelWithRetry(params, MAX_PROMPT_RETRIES);
    }

    private MessageCreateParams buildParams(String systemPrompt, String userPrompt) {
        return MessageCreateParams.builder()
                .model(MODEL)
                .system(systemPrompt)
                // .systemOfTextBlockParams(List.of(
                //     TextBlockParam.builder()
                //         .text(systemPrompt)
                //         .cacheControl(CacheControlEphemeral.builder().build())
                //         .build()
                // )) // Only useful after 1024 tokens
                .addUserMessage(userPrompt)
                .maxTokens(MAX_TOKENS)
                // .temperature(TEMPERATURE) // Not supported when thinking mode is on
                //.topP(TOP_P) // Anthropic does not allow to set temperature and top-p at the same time
                .thinking(ThinkingConfigEnabled.builder().budgetTokens(MAX_TOKENS_THINKING_MODE).build())
                .outputConfig(OutputConfig.builder()
                    .effort(OutputConfig.Effort.HIGH) // Make this explicit for replicability
                    .build())
                .build();
    }
    
    private String askModelWithRetry(MessageCreateParams params, int maxRetries) {
        for (int attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                long start = System.nanoTime();
                Message message = ANTHROPIC.messages().create(params);
                long end = System.nanoTime();

                inputTokens = (int) message.usage().inputTokens();
                outputTokens = (int) message.usage().outputTokens();
                requestTime = (end - start) / 1_000_000.0;

                String responseText = extractResponseText(message);
                if (!responseText.isBlank()) {
                    return responseText;
                }
            } catch (RateLimitException | InternalServerException e) {
                if (attempt >= maxRetries) {
                    throw e;
                }

                // Response in seconds
                String retryAfter = e.headers().values(RETRY_HEADER).stream().findFirst().orElse(DEFAULT_RETRY);
                sleep(Long.parseLong(retryAfter) * 1000L);
            }
        }
        throw new IllegalStateException("Model returned a blank text response after " + maxRetries + " retries");
    }
    
    private void sleep(long ms) {
        try { 
            Thread.sleep(ms); 
        } catch (InterruptedException ie) { 
            Thread.currentThread().interrupt(); 
        }
    }

    private static String extractResponseText(Message message) {
        return message.content().stream()
            .filter(block -> block.isText())
            .map(block -> block.asText().text())
            .collect(Collectors.joining());
    }
}
