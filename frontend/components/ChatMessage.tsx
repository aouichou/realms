 import { Message } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import { TypewriterText } from "./TypewriterText";

interface ChatMessageProps {
	message: Message;
	isStreaming?: boolean;
	enableTypewriter?: boolean; // Enable typewriter effect for DM messages
}

export function ChatMessage({ message, isStreaming, enableTypewriter = false }: ChatMessageProps) {
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
						<div className="whitespace-pre-wrap wrap-break-word">
							{isUser ? (
								message.content
							) : enableTypewriter ? (
								<TypewriterText
									text={message.content}
									speed={120}
									skipAnimation={isStreaming}
								>
									{(displayedText, isComplete, showCursor) => (
										<>
											<ReactMarkdown
												components={{
													h3: ({ children }) => (
														<h3 className="text-lg font-semibold text-gray-100 mt-3 mb-2">
															{children}
														</h3>
													),
													strong: ({ children }) => (
														<strong className="font-semibold text-gray-100">{children}</strong>
													),
													em: ({ children }) => (
														<em className="italic text-gray-200">{children}</em>
													),
													ul: ({ children }) => (
														<ul className="list-disc list-inside space-y-1">{children}</ul>
													),
													ol: ({ children }) => (
														<ol className="list-decimal list-inside space-y-1">{children}</ol>
													),
													li: ({ children }) => <li className="ml-4">{children}</li>,
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
								<ReactMarkdown
									components={{
										h3: ({ children }) => (
											<h3 className="text-lg font-semibold text-gray-100 mt-3 mb-2">
												{children}
											</h3>
										),
										strong: ({ children }) => (
											<strong className="font-semibold text-gray-100">{children}</strong>
										),
										em: ({ children }) => (
											<em className="italic text-gray-200">{children}</em>
										),
										ul: ({ children }) => (
											<ul className="list-disc list-inside space-y-1">{children}</ul>
										),
										ol: ({ children }) => (
											<ol className="list-decimal list-inside space-y-1">{children}</ol>
										),
										li: ({ children }) => <li className="ml-4">{children}</li>,
									}}
								>
									{message.content}
								</ReactMarkdown>
							)}
							{isStreaming && (
								<span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
							)}
						</div>
					</div>
				</div>
				<div className="mt-2 text-xs opacity-60">
					{message.timestamp.toLocaleTimeString()}
				</div>
			</div>
		</div>
	);
}
