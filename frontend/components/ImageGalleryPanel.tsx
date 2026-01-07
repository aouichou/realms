'use client';

import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Download, Expand } from 'lucide-react';
import Image from 'next/image';
import { useState } from 'react';
import { Button } from './ui/button';

interface ImageGalleryPanelProps {
	images: Array<{
		url: string;
		timestamp: string;
		caption?: string;
	}>;
}

export function ImageGalleryPanel({ images }: ImageGalleryPanelProps) {
	const [selectedImage, setSelectedImage] = useState<string | null>(null);

	const downloadImage = async (url: string, index: number) => {
		try {
			const response = await fetch(url);
			const blob = await response.blob();
			const link = document.createElement('a');
			link.href = URL.createObjectURL(blob);
			link.download = `scene-${index + 1}.png`;
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
			URL.revokeObjectURL(link.href);
		} catch (error) {
			console.error('Error downloading image:', error);
		}
	};

	if (images.length === 0) {
		return (
			<div className="flex flex-col items-center justify-center h-full text-white/60 space-y-4 p-8">
				<div className="text-6xl">🖼️</div>
				<p className="text-center font-body">
					No scene images generated yet.<br />
					Images will appear here as your adventure unfolds.
				</p>
			</div>
		);
	}

	return (
		<div className="flex flex-col h-full">
			{/* Full Screen Modal */}
			{selectedImage && (
				<div
					className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
					onClick={() => setSelectedImage(null)}
				>
					<div className="relative max-w-7xl max-h-full">
						<Image
							src={selectedImage}
							alt="Scene"
							width={1200}
							height={800}
							className="rounded-lg object-contain max-h-[90vh]"
						/>
						<button
							onClick={() => setSelectedImage(null)}
							className="absolute top-4 right-4 text-white/80 hover:text-white text-4xl bg-black/50 rounded-full w-12 h-12 flex items-center justify-center backdrop-blur-sm"
						>
							×
						</button>
					</div>
				</div>
			)}

			{/* Header */}
			<div className="mb-4">
				<h3 className="text-lg font-display text-white mb-2">
					Scene Gallery
				</h3>
				<p className="text-sm text-white/60 font-body">
					{images.length} scene{images.length !== 1 ? 's' : ''} captured
				</p>
			</div>

			{/* Image Grid */}
			<ScrollArea className="flex-1">
				<div className="grid grid-cols-1 gap-4 pr-4">
					{images.map((image, index) => (
						<Card
							key={index}
							className="bg-white/5 border-white/10 overflow-hidden hover:border-accent-400/50 transition-all group"
						>
							<div className="relative aspect-video">
								<Image
									src={image.url}
									alt={`Scene ${index + 1}`}
									fill
									className="object-cover"
								/>

								{/* Overlay Actions */}
								<div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
									<Button
										variant="ghost"
										size="icon"
										onClick={() => setSelectedImage(image.url)}
										className="text-white hover:text-accent-400 hover:bg-white/10"
									>
										<Expand className="w-5 h-5" />
									</Button>
									<Button
										variant="ghost"
										size="icon"
										onClick={() => downloadImage(image.url, index)}
										className="text-white hover:text-accent-400 hover:bg-white/10"
									>
										<Download className="w-5 h-5" />
									</Button>
								</div>
							</div>

							{/* Image Info */}
							<div className="p-3 space-y-1">
								<p className="text-xs text-white/80 font-body">
									Scene {images.length - index}
								</p>
								<p className="text-xs text-white/50 font-body">
									{new Date(image.timestamp).toLocaleString()}
								</p>
								{image.caption && (
									<p className="text-xs text-white/70 font-body italic line-clamp-2">
										{image.caption}
									</p>
								)}
							</div>
						</Card>
					))}
				</div>
			</ScrollArea>
		</div>
	);
}
