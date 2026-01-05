import { Message } from "@/lib/api";

interface ChatMessageProps {
	message: Message;
	isStreaming?: boolean;
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
	const isUser = message.role === "user";

	return (
		<div
			className={`flex w-full ${isUser ? "justify-end" : "justify-start"} mb-4`}
		>
			<div
				className={`max-w-[80%] rounded-lg px-4 py-3 ${isUser
					? "bg-purple-600 text-white"
					: "bg-slate-800 text-gray-100 border border-slate-700"
					}`}
			>
				<div className="flex items-start gap-2">
					{!isUser && (
						<span className="text-purple-400 font-semibold text-sm mt-0.5">
							DM:
						</span>
					)}
					<div className="flex-1">
						<p className="whitespace-pre-wrap wrap-break-word">
							{message.content}
							{isStreaming && (
								<span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
							)}
						</p>
					</div>
				</div>
				<div className="mt-2 text-xs opacity-60">
					{message.timestamp.toLocaleTimeString()}
				</div>
			</div>
		</div>
	);
}
