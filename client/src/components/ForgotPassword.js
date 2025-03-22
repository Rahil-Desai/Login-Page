import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './SignIn.css'; // Reusing the same CSS

function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');

  const handleChange = e => {
    setEmail(e.target.value);
    setError('');
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Validate input
    if (!email) {
      setError('Please enter your email');
      setLoading(false);
      return;
    }

    try {
      // Using Flask backend API endpoint
      const response = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'Failed to send reset link');
      }
      
      // Set success message
      setSuccess('Password reset link has been sent to your email');
      setEmail('');
      
    } catch (err) {
      // For security reasons, always show success message even if email doesn't exist
      setSuccess('If the email exists in our system, a password reset link will be sent');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="signin-container">
      <div className="signin-form-wrapper">
        <h1>Reset Password</h1>
        <p className="reset-instructions">
          Enter your email address and we'll send you a link to reset your password.
        </p>
        <form className="signin-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              value={email}
              onChange={handleChange}
              required
            />
          </div>
          {error && <div className="error-message">{error}</div>}
          {success && <div className="success-message">{success}</div>}
          <div className="form-group">
            <button type="submit" disabled={loading}>
              {loading ? 'Sending...' : 'Send Reset Link'}
            </button>
          </div>
        </form>
        <div className="links">
          <Link to="/signin">Back to Sign In</Link>
        </div>
      </div>
    </div>
  );
}

export default ForgotPassword;