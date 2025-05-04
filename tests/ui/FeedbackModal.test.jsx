/**
 * Tests for the FeedbackModal component
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import FeedbackModal from '../../src/ui/components/FeedbackModal';

// Mock fetch function
global.fetch = jest.fn();

describe('FeedbackModal', () => {
  // Reset mocks before each test
  beforeEach(() => {
    fetch.mockClear();
    // Mock successful fetch response
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true })
    });
  });

  it('renders feedback button correctly', () => {
    render(<FeedbackModal userId="test-user" />);
    
    // Check that the button is rendered
    const button = screen.getByRole('button', { name: /open feedback form/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('Feedback');
  });

  it('opens modal when button is clicked', () => {
    render(<FeedbackModal userId="test-user" />);
    
    // Click the button to open the modal
    fireEvent.click(screen.getByRole('button', { name: /open feedback form/i }));
    
    // Check that the modal is open
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Rate your experience')).toBeInTheDocument();
  });

  it('closes modal when cancel button is clicked', () => {
    render(<FeedbackModal userId="test-user" />);
    
    // Open the modal
    fireEvent.click(screen.getByRole('button', { name: /open feedback form/i }));
    
    // Click the cancel button
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    
    // Check that the modal is closed
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('allows rating selection', () => {
    render(<FeedbackModal userId="test-user" />);
    
    // Open the modal
    fireEvent.click(screen.getByRole('button', { name: /open feedback form/i }));
    
    // Select rating 3
    fireEvent.click(screen.getByRole('button', { name: /rate 3 out of 5/i }));
    
    // Check that the rating is selected
    expect(screen.getByRole('button', { name: /rate 3 out of 5/i })).toHaveAttribute('aria-pressed', 'true');
  });

  it('allows comment input', () => {
    render(<FeedbackModal userId="test-user" />);
    
    // Open the modal
    fireEvent.click(screen.getByRole('button', { name: /open feedback form/i }));
    
    // Enter a comment
    fireEvent.change(screen.getByLabelText(/comments/i), { 
      target: { value: 'Great service!' } 
    });
    
    // Check that the comment is entered
    expect(screen.getByLabelText(/comments/i)).toHaveValue('Great service!');
  });

  it('submits feedback when submit button is clicked', async () => {
    render(<FeedbackModal userId="test-user-123" />);
    
    // Open the modal
    fireEvent.click(screen.getByRole('button', { name: /open feedback form/i }));
    
    // Select rating 4
    fireEvent.click(screen.getByRole('button', { name: /rate 4 out of 5/i }));
    
    // Enter a comment
    fireEvent.change(screen.getByLabelText(/comments/i), { 
      target: { value: 'Excellent work!' } 
    });
    
    // Submit the form
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));
    
    // Check that fetch was called with the correct arguments
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(1);
      expect(fetch).toHaveBeenCalledWith('/api/feedback/', {
        method: 'POST',
        body: JSON.stringify({ 
          user_id: 'test-user-123', 
          rating: 4, 
          comments: 'Excellent work!' 
        }),
        headers: { 'Content-Type': 'application/json' }
      });
    });
    
    // Check that the modal is closed after submission
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('shows error message when submission fails', async () => {
    // Mock failed fetch response
    fetch.mockRejectedValueOnce(new Error('Network error'));
    
    render(<FeedbackModal userId="test-user" />);
    
    // Open the modal
    fireEvent.click(screen.getByRole('button', { name: /open feedback form/i }));
    
    // Submit the form
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));
    
    // Check that error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/an error occurred/i)).toBeInTheDocument();
    });
    
    // Check that the modal is still open
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('disables submit button during submission', async () => {
    // Mock delayed fetch response
    fetch.mockImplementationOnce(() => new Promise(resolve => {
      setTimeout(() => {
        resolve({
          ok: true,
          json: async () => ({ ok: true })
        });
      }, 100);
    }));
    
    render(<FeedbackModal userId="test-user" />);
    
    // Open the modal
    fireEvent.click(screen.getByRole('button', { name: /open feedback form/i }));
    
    // Submit the form
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));
    
    // Check that submit button is disabled and shows loading state
    expect(screen.getByRole('button', { name: /submitting/i })).toBeDisabled();
    
    // Wait for submission to complete
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });
});