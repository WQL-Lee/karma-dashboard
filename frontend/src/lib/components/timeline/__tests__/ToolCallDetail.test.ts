import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup, fireEvent, screen } from '@testing-library/svelte';
import ToolCallDetail from '../ToolCallDetail.svelte';
import type { TimelineEvent } from '$lib/api-types';

// Helper to create a minimal timeline event with tool result
function createToolEvent(
	toolName: string,
	resultContent: string,
	resultStatus: 'success' | 'error' = 'success'
): TimelineEvent {
	return {
		id: `evt-${Math.random().toString(36).slice(2)}`,
		timestamp: new Date().toISOString(),
		event_type: 'tool_call',
		title: `${toolName} tool`,
		actor: 'main',
		actor_type: 'main',
		metadata: {
			tool_name: toolName,
			tool_id: `toolu_${toolName.toLowerCase()}_001`,
			has_result: true,
			result_status: resultStatus,
			result_content: resultContent,
			result_timestamp: new Date().toISOString()
		}
	};
}

describe('ToolCallDetail - Collapsible Content', () => {
	// Constants from the component
	const COLLAPSIBLE_TOOLS = new Set(['Write', 'Read', 'Edit', 'Bash', 'Shell']);
	const COLLAPSE_THRESHOLD = 5000;

	afterEach(() => {
		cleanup();
		vi.unstubAllGlobals();
	});

	// =============================================================================
	// Tests for COLLAPSIBLE_TOOLS - Should show collapse button when content > threshold
	// =============================================================================

	describe('Collapsible tools with long content (> 5000 chars)', () => {
		const longContent = 'x'.repeat(6000); // Exceeds COLLAPSE_THRESHOLD

		it('shows "Show more" button for Write tool', async () => {
			const event = createToolEvent('Write', longContent);
			render(ToolCallDetail, { props: { event } });

			const button = screen.getByText(/Show more/);
			expect(button).toBeTruthy();
		});

		it('shows "Show more" button for Read tool', async () => {
			const event = createToolEvent('Read', longContent);
			render(ToolCallDetail, { props: { event } });

			const button = screen.getByText(/Show more/);
			expect(button).toBeTruthy();
		});

		it('shows "Show more" button for Edit tool', async () => {
			const event = createToolEvent('Edit', longContent);
			render(ToolCallDetail, { props: { event } });

			const button = screen.getByText(/Show more/);
			expect(button).toBeTruthy();
		});

		it('shows "Show more" button for Bash tool', async () => {
			const event = createToolEvent('Bash', longContent);
			render(ToolCallDetail, { props: { event } });

			const button = screen.getByText(/Show more/);
			expect(button).toBeTruthy();
		});

		it('shows "Show more" button for Shell tool', async () => {
			const event = createToolEvent('Shell', longContent);
			render(ToolCallDetail, { props: { event } });

			const button = screen.getByText(/Show more/);
			expect(button).toBeTruthy();
		});

		it('displays "--- Output truncated ---" when collapsed', async () => {
			const event = createToolEvent('Write', longContent);
			render(ToolCallDetail, { props: { event } });

			const truncatedMsg = screen.getByText(/--- Output truncated ---/);
			expect(truncatedMsg).toBeTruthy();
		});

		it('shows content size in KB on the button', async () => {
			const event = createToolEvent('Write', longContent);
			render(ToolCallDetail, { props: { event } });

			// 6000 chars ≈ 6KB
			const button = screen.getByText(/Show more.*6KB/);
			expect(button).toBeTruthy();
		});
	});

	// =============================================================================
	// Tests for non-COLLAPSIBLE_TOOLS - Should NOT show collapse button
	// =============================================================================

	describe('Non-collapsible tools (never show collapse button)', () => {
		const longContent = 'x'.repeat(6000);

		it('does NOT show collapse button for Grep tool', async () => {
			const event = createToolEvent('Grep', longContent);
			render(ToolCallDetail, { props: { event } });

			const showMoreBtn = screen.queryByText(/Show more/);
			expect(showMoreBtn).toBeNull();
		});

		it('does NOT show collapse button for Glob tool', async () => {
			const event = createToolEvent('Glob', longContent);
			render(ToolCallDetail, { props: { event } });

			const showMoreBtn = screen.queryByText(/Show more/);
			expect(showMoreBtn).toBeNull();
		});

		it('does NOT show collapse button for WebSearch tool', async () => {
			const event = createToolEvent('WebSearch', longContent);
			render(ToolCallDetail, { props: { event } });

			const showMoreBtn = screen.queryByText(/Show more/);
			expect(showMoreBtn).toBeNull();
		});

		it('does NOT show collapse button for TaskCreate tool', async () => {
			const event = createToolEvent('TaskCreate', longContent);
			render(ToolCallDetail, { props: { event } });

			const showMoreBtn = screen.queryByText(/Show more/);
			expect(showMoreBtn).toBeNull();
		});
	});

	// =============================================================================
	// Tests for short content (< threshold) - No collapse button
	// =============================================================================

	describe('Short content (< 5000 chars) - No collapse button even for collapsible tools', () => {
		const shortContent = 'x'.repeat(4000); // Under COLLAPSE_THRESHOLD

		it('does NOT show collapse button for Write tool with short content', async () => {
			const event = createToolEvent('Write', shortContent);
			render(ToolCallDetail, { props: { event } });

			const showMoreBtn = screen.queryByText(/Show more/);
			expect(showMoreBtn).toBeNull();
		});

		it('does NOT show collapse button for Bash tool with short content', async () => {
			const event = createToolEvent('Bash', shortContent);
			render(ToolCallDetail, { props: { event } });

			const showMoreBtn = screen.queryByText(/Show more/);
			expect(showMoreBtn).toBeNull();
		});

		it('displays full content without truncation message', async () => {
			const event = createToolEvent('Write', shortContent);
			render(ToolCallDetail, { props: { event } });

			const truncatedMsg = screen.queryByText(/--- Output truncated ---/);
			expect(truncatedMsg).toBeNull();
		});
	});

	// =============================================================================
	// Tests for expand/collapse toggle behavior
	// =============================================================================

	describe('Expand/collapse toggle behavior', () => {
		const longContent = 'x'.repeat(6000);

		it('toggles to "Show less" when "Show more" button is clicked', async () => {
			const event = createToolEvent('Write', longContent);
			render(ToolCallDetail, { props: { event } });

			const showMoreBtn = screen.getByText(/Show more/);
			await fireEvent.click(showMoreBtn);

			const showLessBtn = screen.getByText(/Show less/);
			expect(showLessBtn).toBeTruthy();
		});

		it('toggles back to "Show more" when "Show less" button is clicked', async () => {
			const event = createToolEvent('Write', longContent);
			render(ToolCallDetail, { props: { event } });

			// First click - expand
			const showMoreBtn = screen.getByText(/Show more/);
			await fireEvent.click(showMoreBtn);

			// Second click - collapse
			const showLessBtn = screen.getByText(/Show less/);
			await fireEvent.click(showLessBtn);

			const showMoreBtnAfter = screen.getByText(/Show more/);
			expect(showMoreBtnAfter).toBeTruthy();
		});

		it('removes "--- Output truncated ---" message when expanded', async () => {
			const event = createToolEvent('Write', longContent);
			render(ToolCallDetail, { props: { event } });

			// Initially shows truncated message
			expect(screen.getByText(/--- Output truncated ---/)).toBeTruthy();

			// Click to expand
			const showMoreBtn = screen.getByText(/Show more/);
			await fireEvent.click(showMoreBtn);

			// Truncated message should be gone
			const truncatedMsg = screen.queryByText(/--- Output truncated ---/);
			expect(truncatedMsg).toBeNull();
		});
	});

	// =============================================================================
	// Tests for error state
	// =============================================================================

	describe('Error state handling', () => {
		const longContent = 'x'.repeat(6000);

		it('shows collapse button for error result with long content', async () => {
			const event = createToolEvent('Write', longContent, 'error');
			render(ToolCallDetail, { props: { event } });

			const button = screen.getByText(/Show more/);
			expect(button).toBeTruthy();
		});
	});
});