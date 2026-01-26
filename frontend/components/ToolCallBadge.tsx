/**
 * ToolCallBadge component - displays which tools DM used
 * Optional showcase component for RL-129 Mistral tool calling demo
 */

interface ToolCallBadgeProps {
	toolName: string;
	arguments?: Record<string, any>;
}

export function ToolCallBadge({ toolName, arguments: args }: ToolCallBadgeProps) {
	// Tool name display mapping
	const toolDisplayNames: Record<string, string> = {
		request_player_roll: '🎲 Roll Request',
		update_character_hp: '❤️ HP Update',
		consume_spell_slot: '✨ Spell Slot',
		get_creature_stats: '👾 Creature Stats',
	};

	// Tool-specific colors
	const toolColors: Record<string, string> = {
		request_player_roll: 'bg-accent-400/20 text-accent-300 border-accent-400/40',
		update_character_hp: 'bg-red-500/20 text-red-300 border-red-500/40',
		consume_spell_slot: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
		get_creature_stats: 'bg-green-500/20 text-green-300 border-green-500/40',
	};

	const displayName = toolDisplayNames[toolName] || toolName;
	const colorClass = toolColors[toolName] || 'bg-neutral-700/50 text-neutral-300 border-neutral-600/50';

	return (
		<div
			className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border backdrop-blur-sm text-xs font-medium ${colorClass}`}
			title={`DM used: ${toolName}${args ? `\n${JSON.stringify(args, null, 2)}` : ''}`}
		>
			<span>{displayName}</span>
		</div>
	);
}

interface ToolCallsBadgeContainerProps {
	toolCalls?: Array<{
		name: string;
		arguments: Record<string, any>;
		result: Record<string, any>;
	}>;
}

/**
 * Container that displays all tool calls made for a message
 */
export function ToolCallsBadgeContainer({ toolCalls }: ToolCallsBadgeContainerProps) {
	if (!toolCalls || toolCalls.length === 0) return null;

	return (
		<div className="flex flex-wrap gap-1.5 mt-2 mb-1">
			{toolCalls.map((toolCall, index) => (
				<ToolCallBadge
					key={`${toolCall.name}-${index}`}
					toolName={toolCall.name}
					arguments={toolCall.arguments}
				/>
			))}
		</div>
	);
}
