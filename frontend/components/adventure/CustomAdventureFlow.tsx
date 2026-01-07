"use client";

import AdventurePreview from "@/components/adventure/AdventurePreview";
import CustomAdventureWizard from "@/components/adventure/CustomAdventureWizard";
import { useRouter } from "next/navigation";
import { useState } from "react";

interface Adventure {
	id: string;
	character_id: string;
	setting: string;
	goal: string;
	tone: string;
	title: string;
	description: string;
	scenes: any[];
	is_completed: boolean;
	created_at: string;
}

interface CustomAdventureFlowProps {
	characterId: string;
	onComplete?: () => void;
	onCancel?: () => void;
}

/**
 * Complete flow for custom adventure creation.
 * Shows wizard -> generates adventure -> displays preview -> starts game
 */
export default function CustomAdventureFlow({
	characterId,
	onComplete,
	onCancel,
}: CustomAdventureFlowProps) {
	const router = useRouter();
	const [adventure, setAdventure] = useState<Adventure | null>(null);

	const handleWizardComplete = (adventureId: string, generatedAdventure: Adventure) => {
		// Store the generated adventure for preview
		setAdventure(generatedAdventure);
	};

	const handleStartAdventure = async (adventureId: string) => {
		// TODO: Create game session with this adventure
		// For now, redirect to game page
		router.push(`/game/${adventureId}`);
		onComplete?.();
	};

	const handleCancel = () => {
		if (adventure) {
			// Go back to wizard
			setAdventure(null);
		} else {
			// Exit flow
			onCancel?.();
		}
	};

	return (
		<div className="min-h-screen">
			{!adventure ? (
				<CustomAdventureWizard
					characterId={characterId}
					onComplete={handleWizardComplete}
					onCancel={handleCancel}
				/>
			) : (
				<AdventurePreview
					adventure={adventure}
					onStart={handleStartAdventure}
					onCancel={handleCancel}
				/>
			)}
		</div>
	);
}
