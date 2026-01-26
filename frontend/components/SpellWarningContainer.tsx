'use client';

import { useCallback, useState } from 'react';
import { SpellWarning } from './SpellWarning';

interface Warning {
	id: string;
	message: string;
	type: 'warning' | 'suggestion' | 'error';
}

interface SpellWarningContainerProps {
	warnings: Warning[];
	onWarningDismissed?: (id: string) => void;
}

export function SpellWarningContainer({ warnings, onWarningDismissed }: SpellWarningContainerProps) {
	const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

	const handleDismiss = useCallback((id: string) => {
		setDismissedIds(prev => new Set([...prev, id]));
		onWarningDismissed?.(id);
	}, [onWarningDismissed]);

	const visibleWarnings = warnings.filter(w => !dismissedIds.has(w.id));

	if (visibleWarnings.length === 0) return null;

	return (
		<div className="fixed top-4 right-4 z-50 w-full max-w-md space-y-3 pointer-events-none">
			<div className="pointer-events-auto space-y-3">
				{visibleWarnings.map(warning => (
					<div
						key={warning.id}
						className="animate-in slide-in-from-right-full duration-300"
					>
						<SpellWarning
							message={warning.message}
							type={warning.type}
							onDismiss={() => handleDismiss(warning.id)}
							duration={warning.type === 'suggestion' ? 7000 : 5000}
						/>
					</div>
				))}
			</div>
		</div>
	);
}
