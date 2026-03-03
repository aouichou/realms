import { describe, expect, it } from 'vitest';
import { willExpireSoon } from '../jwt';

// Helper: create a mock JWT with a given expiry timestamp
function createMockJwt(payload: Record<string, unknown>): string {
	const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
	const body = btoa(JSON.stringify(payload));
	const sig = 'fake-signature';
	return `${header}.${body}.${sig}`;
}

describe('JWT utilities', () => {
	describe('willExpireSoon', () => {
		it('returns true when token expires within the threshold', () => {
			const expiresInOneMinute = Math.floor(Date.now() / 1000) + 60;
			const token = createMockJwt({ sub: 'user1', exp: expiresInOneMinute, type: 'access' });
			// Default threshold is 5 minutes (300_000 ms). 1 minute < 5 minutes => true
			expect(willExpireSoon(token)).toBe(true);
		});

		it('returns false when token has plenty of time left', () => {
			const expiresInTenMinutes = Math.floor(Date.now() / 1000) + 600;
			const token = createMockJwt({ sub: 'user1', exp: expiresInTenMinutes, type: 'access' });
			expect(willExpireSoon(token)).toBe(false);
		});

		it('returns true when token is already expired', () => {
			const expiredOneMinuteAgo = Math.floor(Date.now() / 1000) - 60;
			const token = createMockJwt({ sub: 'user1', exp: expiredOneMinuteAgo, type: 'access' });
			expect(willExpireSoon(token)).toBe(true);
		});

		it('returns false for an invalid token', () => {
			expect(willExpireSoon('not-a-jwt')).toBe(false);
		});

		it('respects a custom threshold', () => {
			const expiresInTwoMinutes = Math.floor(Date.now() / 1000) + 120;
			const token = createMockJwt({ sub: 'user1', exp: expiresInTwoMinutes, type: 'access' });

			// 2 minutes left, threshold 1 minute => not expiring soon
			expect(willExpireSoon(token, 60_000)).toBe(false);

			// 2 minutes left, threshold 3 minutes => expiring soon
			expect(willExpireSoon(token, 180_000)).toBe(true);
		});

		it('returns false if token has no exp claim', () => {
			const token = createMockJwt({ sub: 'user1', type: 'access' });
			expect(willExpireSoon(token)).toBe(false);
		});
	});
});
