"use client";

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Maximize2 } from "lucide-react";
import Image from "next/image";
import { useState } from "react";

interface SceneImageProps {
	imageUrl: string;
	alt?: string;
}

export function SceneImage({ imageUrl, alt = "Scene illustration" }: SceneImageProps) {
	const [isFullscreen, setIsFullscreen] = useState(false);
	const [isLoading, setIsLoading] = useState(true);

	return (
		<>
			<div className="relative w-full aspect-[16/9] mb-3 rounded-lg overflow-hidden group">
				{/* Loading skeleton */}
				{isLoading && (
					<div className="absolute inset-0 bg-gradient-to-r from-white/5 via-white/10 to-white/5 animate-pulse" />
				)}

				{/* Image */}
				<Image
					src={imageUrl}
					alt={alt}
					fill
					className={`object-cover transition-all duration-300 ${isLoading ? 'opacity-0' : 'opacity-100'
						}`}
					onLoadingComplete={() => setIsLoading(false)}
					priority
				/>

				{/* Fullscreen button */}
				<button
					onClick={() => setIsFullscreen(true)}
					className="absolute top-2 right-2 p-2 bg-black/60 backdrop-blur-sm rounded-lg
                     opacity-0 group-hover:opacity-100 transition-opacity
                     text-white hover:bg-black/80"
					aria-label="View fullscreen"
				>
					<Maximize2 className="h-4 w-4" />
				</button>

				{/* Fade-in overlay */}
				<div
					className={`absolute inset-0 bg-gradient-to-t from-black/40 to-transparent pointer-events-none
                     transition-opacity duration-500 ${isLoading ? 'opacity-0' : 'opacity-100'}`}
				/>
			</div>

			{/* Fullscreen Dialog */}
			<Dialog open={isFullscreen} onOpenChange={setIsFullscreen}>
				<DialogContent className="max-w-[95vw] max-h-[95vh] p-0">
					<div className="relative w-full h-[90vh]">
						<Image
							src={imageUrl}
							alt={alt}
							fill
							className="object-contain"
							priority
						/>
					</div>
				</DialogContent>
			</Dialog>
		</>
	);
}
