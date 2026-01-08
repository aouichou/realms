'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function AdventurePage() {
	const router = useRouter();

	useEffect(() => {
		// Get selected character from localStorage
		const characterId = localStorage.getItem('selected_character_id');

		if (characterId) {
			// Redirect to adventure selection for this character
			router.push(`/adventure/select/${characterId}`);
		} else {
			// No character selected, go back to character selection
			router.push('/character/select');
		}
	}, [router]);

	return (
		<div className="flex min-h-screen items-center justify-center">
			<div className="text-center">
				<div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary-900 mx-auto mb-4"></div>
				<p className="text-neutral-500">Loading...</p>
			</div>
		</div>
	);
}
