// API client configuration and utilities

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Message {
	role: "user" | "assistant";
	content: string;
	timestamp: Date;
}

export interface NarrateRequest {
	action: string;
	character_context?: Record<string, unknown>;
	game_state?: Record<string, unknown>;
}

export interface NarrateResponse {
	narration: string;
	tokens_used: number;
}

/**
 * Send a player action and get narration (non-streaming)
 */
export async function narrate(
	request: NarrateRequest
): Promise<NarrateResponse> {
	const response = await fetch(`${API_URL}/api/narrate`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify(request),
	});

	if (!response.ok) {
		throw new Error(`API error: ${response.status}`);
	}

	return response.json();
}

/**
 * Send a player action and get streaming narration
 */
export async function* narrateStream(
	request: NarrateRequest
): AsyncGenerator<string, void, unknown> {
	const response = await fetch(`${API_URL}/api/narrate/stream`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify(request),
	});

	if (!response.ok) {
		throw new Error(`API error: ${response.status}`);
	}

	const reader = response.body?.getReader();
	if (!reader) {
		throw new Error("No response body");
	}

	const decoder = new TextDecoder();

	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			const chunk = decoder.decode(value, { stream: true });
			const lines = chunk.split("\n");

			for (const line of lines) {
				if (line.startsWith("data: ")) {
					const data = line.slice(6).trim();
					if (data === "[DONE]") {
						return;
					}
					if (data) {
						yield data;
					}
				}
			}
		}
	} finally {
		reader.releaseLock();
	}
}

/**
 * Start a new adventure (non-streaming)
 */
export async function startAdventure(): Promise<NarrateResponse> {
	const response = await fetch(`${API_URL}/api/adventure/start`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
	});

	if (!response.ok) {
		throw new Error(`API error: ${response.status}`);
	}

	return response.json();
}

/**
 * Start a new adventure with streaming
 */
export async function* startAdventureStream(): AsyncGenerator<
	string,
	void,
	unknown
> {
	const response = await fetch(`${API_URL}/api/adventure/start/stream`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
	});

	if (!response.ok) {
		throw new Error(`API error: ${response.status}`);
	}

	const reader = response.body?.getReader();
	if (!reader) {
		throw new Error("No response body");
	}

	const decoder = new TextDecoder();

	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			const chunk = decoder.decode(value, { stream: true });
			const lines = chunk.split("\n");

			for (const line of lines) {
				if (line.startsWith("data: ")) {
					const data = line.slice(6).trim();
					if (data === "[DONE]") {
						return;
					}
					if (data) {
						yield data;
					}
				}
			}
		}
	} finally {
		reader.releaseLock();
	}
}

/**
 * Check API health
 */
export async function checkHealth(): Promise<{
	status: string;
	app_name: string;
	version: string;
	environment: string;
}> {
	const response = await fetch(`${API_URL}/health`);

	if (!response.ok) {
		throw new Error(`API error: ${response.status}`);
	}

	return response.json();
}
