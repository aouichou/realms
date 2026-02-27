// API client configuration and utilities

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Message {
	role: "user" | "assistant";
	content: string;
	timestamp: Date;
	scene_image_url?: string;
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
