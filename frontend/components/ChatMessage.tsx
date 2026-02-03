import ReactMarkdown from "react-markdown";
import CompanionMessage from "./CompanionMessage";
import NPCRollResult from "./NPCRollResult";
import { ToolCallsBadgeContainer } from "./ToolCallBadge";
import { TypewriterText } from "./TypewriterText";

// Extended Message interface matching the game page
interface Message {
	id: number;
	role: 'user' | 'assistant' | 'companion';
	content: string;
	timestamp: string;
	scene_image_url?: string;
	quest_complete_id?: string;
	warnings?: string[];
	companion_id?: string;
	companion_name?: string;
	companion_data?: {
		id: number;
		name: string;
		creature_name: string;
		relationship_status: string;
		loyalty: number;
		hp: number;
		max_hp: number;
		ac: number;
		avatar_url?: string;
		personality: string;
	};
	tool_calls_made?: Array<{
		name: string;
		arguments: Record<string, any>;
		result: Record<string, any>;
	}>;
	character_updates?: any;
}

interface ChatMessageProps {
	message: Message;
	isStreaming?: boolean;
	enableTypewriter?: boolean;
}

export function ChatMessage({ message, isStreaming, enableTypewriter = true }: ChatMessageProps) {
	// Handle companion messages separately
	if (message.role === 'companion' && message.companion_data) {
		return (
			<div className="mr-6 md:mr-12">
				<CompanionMessage
					companion={message.companion_data}
					message={message.content}
					showStats={true}
				/>
			</div>
		);
	}

	// Handle user/assistant messages
	const isUser = message.role === 'user';

	return (
		<div
			className={`p-3 md:p-4 rounded-lg backdrop-blur-md ${isUser
				? 'bg-accent-400/20 border border-accent-400/30 ml-6 md:ml-12'
				: 'bg-white/10 border border-white/20 mr-6 md:mr-12'
				}`}
		>
			<div className="flex items-center gap-2 mb-2">
				<span className="font-display text-sm text-white">
					{isUser ? 'You' : 'Dungeon Master'}
				</span>
				{message.role === 'assistant' && (
					<span className="text-xs font-body font-bold tracking-wide bg-accent-400 text-primary-900 px-2 py-0.5 rounded">
						AI
					</span>
				)}
			</div>

			{/* Scene image for DM messages */}
			{message.role === 'assistant' && message.scene_image_url && (
				<div className="mb-3">
					<img
						src={message.scene_image_url}
						alt="Scene illustration"
						className="w-full rounded-lg border border-white/30"
					/>
				</div>
			)}

			{/* Tool calls badge */}
			{message.tool_calls_made && message.tool_calls_made.length > 0 && (
				<ToolCallsBadgeContainer toolCalls={message.tool_calls_made} />
			)}

			{/* NPC roll results */}
			{message.tool_calls_made
				?.filter(call => call.name === 'roll_for_npc' && call.result?.success)
				.map((call, idx) => (
					<NPCRollResult
						key={`npc-roll-${idx}`}
						roll={call.result as any}
					/>
				))}

			{/* Message content */}
			<div className="text-narrative text-white font-body leading-relaxed whitespace-pre-line">
				{message.role === 'assistant' && enableTypewriter ? (
					<TypewriterText text={message.content} speed={120}>
						{(displayedText, isComplete, showCursor) => (
							<>
								<ReactMarkdown
									components={{
										h3: ({ children }) => (
											<h3 className="text-xl font-display text-white mt-3 mb-2">{children}</h3>
										),
										strong: ({ children }) => (
											<strong className="font-semibold text-white">{children}</strong>
										),
										em: ({ children }) => (
											<em className="italic text-white/90">{children}</em>
										),
										ul: ({ children }) => (
											<ul className="list-disc list-inside space-y-1">{children}</ul>
										),
										ol: ({ children }) => (
											<ol className="list-decimal list-inside space-y-1">{children}</ol>
										),
										li: ({ children }) => (
											<li className="ml-4">{children}</li>
										),
									}}
								>
									{displayedText}
								</ReactMarkdown>
								{showCursor && (
									<span className="inline-block w-1 h-4 ml-0.5 bg-purple-400 animate-pulse" />
								)}
							</>
						)}
					</TypewriterText>
				) : (
					message.content
				)}
			</div>
		</div>
	);
}
