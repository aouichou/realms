import { ReactNode, useEffect, useState } from 'react';

interface TypewriterTextProps {
	text: string;
	speed?: number; // characters per second (default: 120)
	onComplete?: () => void;
	skipAnimation?: boolean;
	children?: (displayedText: string, isComplete: boolean, showCursor: boolean) => ReactNode;
}

/**
 * Typewriter/teleprompter effect component for displaying text character-by-character.
 *
 * Features:
 * - Configurable speed (default ~120 chars/sec for faster, comfortable reading)
 * - Skip animation by clicking
 * - Callback when animation completes
 * - Supports render prop pattern for custom rendering (e.g., with Markdown)
 *
 * @example
 * // Simple usage
 * <TypewriterText text="The dragon breathes fire!" />
 *
 * @example
 * // With Markdown renderer
 * <TypewriterText text={message}>
 *   {(text, isComplete, showCursor) => <ReactMarkdown>{text}</ReactMarkdown>}
 * </TypewriterText>
 */
export function TypewriterText({
	text,
	speed = 120,
	onComplete,
	skipAnimation = false,
	children
}: TypewriterTextProps) {
	const [displayedText, setDisplayedText] = useState('');
	const [isComplete, setIsComplete] = useState(false);
	const [isSkipped, setIsSkipped] = useState(skipAnimation);
	const [showCursor, setShowCursor] = useState(true);

	useEffect(() => {
		// Reset when text changes
		setDisplayedText('');
		setIsComplete(false);
		setIsSkipped(skipAnimation);
		setShowCursor(true);
	}, [text, skipAnimation]);

	useEffect(() => {
		// Skip animation if requested
		if (isSkipped) {
			setDisplayedText(text);
			setIsComplete(true);
			onComplete?.();
			return;
		}

		// Already complete, no need to animate
		if (isComplete || displayedText === text) {
			return;
		}

		// Calculate delay in milliseconds between characters
		const delay = 1000 / speed;

		const timer = setTimeout(() => {
			if (displayedText.length < text.length) {
				setDisplayedText(text.slice(0, displayedText.length + 1));
			} else {
				setIsComplete(true);
				// Keep cursor visible for a brief moment after completion
				setTimeout(() => setShowCursor(false), 500);
				onComplete?.();
			}
		}, delay);

		return () => clearTimeout(timer);
	}, [displayedText, text, speed, isComplete, isSkipped, onComplete]);

	const handleClick = () => {
		if (!isComplete) {
			setDisplayedText(text);
			setIsComplete(true);
			setIsSkipped(true);
			// Keep cursor visible briefly when skipped too
			setTimeout(() => setShowCursor(false), 300);
			onComplete?.();
		}
	};

	return (
		<div
			onClick={handleClick}
			className={!isComplete ? 'cursor-pointer' : ''}
			title={!isComplete ? 'Click to skip animation' : undefined}
		>
			{children ? (
				children(displayedText, isComplete, showCursor)
			) : (
				<>
					{displayedText}
					{showCursor && (
						<span className="inline-block w-1 h-4 ml-0.5 bg-current animate-pulse" />
					)}
				</>
			)}
		</div>
	);
}
