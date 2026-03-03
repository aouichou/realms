import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [react()],
	test: {
		environment: 'jsdom',
		globals: true,
		setupFiles: ['./vitest.setup.ts'],
		include: ['**/__tests__/**/*.{test,spec}.{ts,tsx}', '**/*.{test,spec}.{ts,tsx}'],
		exclude: ['node_modules', '.next', 'e2e'],
		coverage: {
			provider: 'v8',
			reporter: ['text', 'lcov', 'clover'],
			include: ['lib/**/*.ts', 'components/**/*.tsx'],
			exclude: ['**/*.d.ts', '**/*.test.*', '**/*.spec.*'],
		},
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, '.'),
		},
	},
});
