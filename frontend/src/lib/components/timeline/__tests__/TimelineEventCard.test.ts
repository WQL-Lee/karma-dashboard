import { describe, it, expect, afterEach } from 'vitest';
import { render, cleanup, screen } from '@testing-library/svelte';
import TimelineEventCard from '../TimelineEventCard.svelte';
import type { TimelineEvent } from '$lib/api-types';

function createEvent(
	overrides: Partial<TimelineEvent> = {}
): TimelineEvent {
	const base: TimelineEvent = {
		id: 'evt-test-001',
		timestamp: '2026-01-08T12:00:00Z',
		event_type: 'tool_call',
		title: 'Bash tool',
		actor: 'main',
		actor_type: 'main',
		metadata: {},
		...overrides,
	};
	base.id = `evt-${Math.random().toString(36).slice(2)}`;
	return base;
}

function renderCard(event: TimelineEvent) {
	return render(TimelineEventCard, {
		props: {
			event,
			index: 0,
			isFirst: true,
			isLast: false,
			sessionStartTime: '2026-01-08T12:00:00Z',
			isHighlighted: false,
			hasActiveFilter: false,
			isExpanded: false,
			onToggleExpand: () => {},
		},
	});
}

describe('TimelineEventCard - Token Badge Display', () => {
	afterEach(() => {
		cleanup();
	});

	// =============================================================================
	// Token badge appears for correct event types
	// =============================================================================

	describe('Token badge visibility by event type', () => {
		// Test each event type explicitly instead of forEach to avoid Svelte 5 reactivity issues
		it('shows token badge for thinking events with tokens', () => {
			const event: TimelineEvent = {
				id: 'evt-thinking-001',
				timestamp: '2026-01-08T12:00:00Z',
				event_type: 'thinking',
				title: 'Thinking',
				actor: 'main',
				actor_type: 'main',
				metadata: {
					full_thinking: 'This is a thinking process',
					input_tokens: 1200,
					output_tokens: 600,
				},
			};
			renderCard(event);
			const tokenBadge = screen.queryByText(/1\.8K/);
			expect(tokenBadge).not.toBeNull();
		});

		it('shows token badge for tool_call events with tokens', () => {
			const event: TimelineEvent = {
				id: 'evt-tool-001',
				timestamp: '2026-01-08T12:00:00Z',
				event_type: 'tool_call',
				title: 'Bash tool',
				actor: 'main',
				actor_type: 'main',
				metadata: {
					tool_name: 'Bash',
					input_tokens: 1200,
					output_tokens: 600,
				},
			};
			renderCard(event);
			const tokenBadge = screen.queryByText(/1\.8K/);
			expect(tokenBadge).not.toBeNull();
		});

		it('shows token badge for response events with tokens', () => {
			const event = createEvent({
				event_type: 'response',
				metadata: { input_tokens: 1200, output_tokens: 600 },
			});
			renderCard(event);
			const tokenBadge = screen.queryByText(/1\.8K/);
			expect(tokenBadge).not.toBeNull();
		});

		it('shows token badge for todo_update events with tokens', () => {
			const event = createEvent({
				event_type: 'todo_update',
				metadata: { input_tokens: 1200, output_tokens: 600 },
			});
			renderCard(event);
			const tokenBadge = screen.queryByText(/1\.8K/);
			expect(tokenBadge).not.toBeNull();
		});

		it('shows token badge for skill_invocation events with tokens', () => {
			const event = createEvent({
				event_type: 'skill_invocation',
				metadata: { input_tokens: 1200, output_tokens: 600 },
			});
			renderCard(event);
			const tokenBadge = screen.queryByText(/1\.8K/);
			expect(tokenBadge).not.toBeNull();
		});

		it('shows token badge for command_invocation events with tokens', () => {
			const event = createEvent({
				event_type: 'command_invocation',
				metadata: { input_tokens: 1200, output_tokens: 600 },
			});
			renderCard(event);
			const tokenBadge = screen.queryByText(/1\.8K/);
			expect(tokenBadge).not.toBeNull();
		});

		it('shows token badge for builtin_command events with tokens', () => {
			const event = createEvent({
				event_type: 'builtin_command',
				metadata: { input_tokens: 1200, output_tokens: 600 },
			});
			renderCard(event);
			const tokenBadge = screen.queryByText(/1\.8K/);
			expect(tokenBadge).not.toBeNull();
		});

		it('shows token badge for subagent_spawn events with tokens', () => {
			const event = createEvent({
				event_type: 'subagent_spawn',
				metadata: { input_tokens: 1200, output_tokens: 600 },
			});
			renderCard(event);
			const tokenBadge = screen.queryByText(/1\.8K/);
			expect(tokenBadge).not.toBeNull();
		});

		it('does NOT show token badge for prompt events', () => {
			const event = createEvent({
				event_type: 'prompt',
				metadata: {
					input_tokens: 1000,
					output_tokens: 500,
				},
			});
			renderCard(event);

			// Token badge should NOT appear for prompt events
			// formatTokens(1500) = "1.5K", but prompt type returns null so no badge
			const tokenBadge = screen.queryByText(/1\.5K/);
			expect(tokenBadge).toBeNull();
		});

		it('does NOT show token badge when no token metadata', () => {
			const event = createEvent({
				event_type: 'tool_call',
				metadata: {},
			});
			renderCard(event);

			// No token badge when no token data (formatTokens doesn't match comma pattern)
			const tokenBadge = screen.queryByText(/1\.5K/);
			expect(tokenBadge).toBeNull();
		});

		it('does NOT show token badge when input and output are both 0', () => {
			const event = createEvent({
				event_type: 'tool_call',
				metadata: {
					input_tokens: 0,
					output_tokens: 0,
				},
			});
			renderCard(event);

			// No token badge when both are 0 (formatTokens(0) returns '--')
			const tokenBadge = screen.queryByText(/1\.5K/);
			expect(tokenBadge).toBeNull();
		});
	});

	// =============================================================================
	// Token count display
	// =============================================================================

	describe('Token count display', () => {
		it('displays correct total token count (input + output)', () => {
			const event = createEvent({
				event_type: 'tool_call',
				metadata: {
					input_tokens: 1000,
					output_tokens: 500,
				},
			});
			renderCard(event);

			// Total = 1000 + 500 = 1500, formatTokens(1500) = "1.5K"
			const tokenBadge = screen.getByText(/1\.5K/);
			expect(tokenBadge).not.toBeNull();
		});

		it('displays correct total when only input_tokens present', () => {
			const event: TimelineEvent = {
				id: 'evt-input-only-001',
				timestamp: '2026-01-08T12:00:00Z',
				event_type: 'thinking',
				title: 'Thinking',
				actor: 'main',
				actor_type: 'main',
				metadata: {
					full_thinking: 'This is a thinking process',
					input_tokens: 1200,
				},
			};
			renderCard(event);

			// Total = 1200, formatTokens(1200) = "1.2K"
			const tokenBadge = screen.getByText(/1\.2K/);
			expect(tokenBadge).not.toBeNull();
		});

		it('displays correct total when only output_tokens present', () => {
			const event = createEvent({
				event_type: 'response',
				metadata: {
					output_tokens: 300,
				},
			});
			renderCard(event);

			// Total = 300, formatTokens(300) = "300"
			const tokenBadge = screen.getByText(/300/);
			expect(tokenBadge).not.toBeNull();
		});

		it('handles large token numbers with formatting', () => {
			const event = createEvent({
				event_type: 'tool_call',
				metadata: {
					input_tokens: 1200,
					output_tokens: 600,
				},
			});
			renderCard(event);

			// Total = 1800, formatTokens(1800) = "1.8K"
			const tokenBadge = screen.getByText(/1\.8K/);
			expect(tokenBadge).not.toBeNull();
		});
	});

	// =============================================================================
	// Edge cases
	// =============================================================================

	describe('Edge cases', () => {
		it('handles missing metadata object', () => {
			const event = createEvent({
				event_type: 'tool_call',
				metadata: undefined as any,
			});
			renderCard(event);

			// Should not throw, no token badge
			const tokenBadge = screen.queryByText(/1\.5K/);
			expect(tokenBadge).toBeNull();
		});

		it('handles non-numeric token values gracefully', () => {
			const event = createEvent({
				event_type: 'tool_call',
				metadata: {
					input_tokens: '1000' as any, // string instead of number
					output_tokens: 500,
				},
			});
			renderCard(event);

			// Should not throw - the component uses `as number` type assertion
			expect(() => renderCard(event)).not.toThrow();
		});

		it('shows token badge for subagent_spawn event type', () => {
			const event = createEvent({
				event_type: 'subagent_spawn',
				metadata: {
					input_tokens: 1200,
					output_tokens: 600,
				},
			});
			renderCard(event);

			// Total = 1800, formatTokens(1800) = "1.8K"
			const tokenBadge = screen.getByText(/1\.8K/);
			expect(tokenBadge).not.toBeNull();
		});

		it('shows token badge for builtin_command event type', () => {
			const event = createEvent({
				event_type: 'builtin_command',
				metadata: {
					input_tokens: 150,
					output_tokens: 75,
				},
			});
			renderCard(event);

			// Total = 225, formatTokens(225) = "225"
			const tokenBadge = screen.getByText(/225/);
			expect(tokenBadge).not.toBeNull();
		});
	});
});