package com.github.alien.tool;


import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.errors.InternalServerException;
import com.openai.errors.RateLimitException;
import com.openai.models.ChatModel;
import com.openai.models.Reasoning;
import com.openai.models.ReasoningEffort;
import com.openai.models.responses.Response;
import com.openai.models.responses.ResponseCreateParams;

public class OpenAI extends LLMTool {
	private static final OpenAIClient OPENAI = OpenAIOkHttpClient.builder()
		.apiKey(dotenv.get("OPENAI_API_KEY"))
		.build();
	private static final String MODEL_NAME = "gpt-5.4";
	private static final String RETRY_HEADER = "retry-after";
	private static final long DEFAULT_RETRY_MS = 1000L;

	@Override
	public String getName() {
		return "gpt-5.4";
	}

	@Override
	protected String askModel(String systemPrompt, String userPrompt) {
		var params = buildParams(systemPrompt, userPrompt);
		return askModelWithRetry(params, MAX_PROMPT_RETRIES);
	}

	private ResponseCreateParams buildParams(String systemPrompt, String userPrompt) {
		return ResponseCreateParams.builder()
			.model(ChatModel.of(MODEL_NAME))
			.instructions(systemPrompt)
			.input(userPrompt)
			.maxOutputTokens(MAX_TOKENS)
			//.temperature(TEMPERATURE) // Not supported when reasoning mode is not "none"
			//.topP(TOP_P) // Not supported when reasoning mode is not "none"
			.reasoning(Reasoning.builder()
				.effort(ReasoningEffort.HIGH) // Make this explicit for replicability
				.build())
			// .parallelToolCalls(false)
			.build();
	}

	

	private String askModelWithRetry(ResponseCreateParams params, int maxRetries) {
		for (int attempt = 0; attempt <= maxRetries; attempt++) {
			try {
				long start = System.nanoTime();
				Response response = OPENAI.responses().create(params);
				long end = System.nanoTime();

				response.usage().ifPresent(usage -> {
					inputTokens = (int) usage.inputTokens();
					outputTokens = (int) usage.outputTokens();
				});

				requestTime = (end - start) / 1_000_000.0;

				var responseText = extractResponseText(response);
				if (!responseText.isBlank()) {
					return responseText;
				}
			} catch (RateLimitException | InternalServerException e) {
				if (attempt >= maxRetries) {
					throw e;
				}
				String retryAfter = e.headers().values(RETRY_HEADER).stream().findFirst().orElse(null);
				long delay = retryAfter != null ? Long.parseLong(retryAfter) * 1000L : DEFAULT_RETRY_MS;
				sleep(delay);
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

	private static String extractResponseText(Response response) {
		var outputText = new StringBuilder();
		for (var outputItem : response.output()) {
			if (!outputItem.isMessage()) {
				continue;
			}
			for (var content : outputItem.asMessage().content()) {
				if (content.isOutputText()) {
					outputText.append(content.asOutputText().text()).append('\n');
				}
			}
		}
		return outputText.toString().trim();
	}

}
