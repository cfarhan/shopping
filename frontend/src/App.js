import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import Landing from './components/Landing';
import Shop from './components/Shop';
import SignUp from './components/SignUp';
import SignIn from './components/SignIn';
import Cart from './components/Cart';

function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      // You could verify token here if needed
      setUser({ token });
    }
  }, [token]);

  const login = (userData, accessToken) => {
    setUser(userData);
    setToken(accessToken);
    localStorage.setItem('token', accessToken);
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
  };

  return (
    <Router>
      <div className="App">
        <nav className="navbar">
          <div className="navbar-content">
            <Link to="/" className="navbar-brand">Shop</Link>
            
            <div className="navbar-nav">
              <Link to="/" className="nav-link">Home</Link>
              <Link to="/shop" className="nav-link">Shop</Link>
              
              {user ? (
                <>
                  <Link to="/cart" className="nav-link">Cart</Link>
                  <span className="user-info">Welcome, {user.email || 'User'}!</span>
                  <button onClick={logout} className="nav-button">Logout</button>
                </>
              ) : (
                <>
                  <Link to="/signin" className="nav-link">Sign In</Link>
                  <Link to="/signup" className="nav-link">Sign Up</Link>
                </>
              )}
            </div>
          </div>
        </nav>

        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/shop" element={<Shop token={token} />} />
          <Route path="/signup" element={
            user ? <Navigate to="/shop" /> : <SignUp onLogin={login} />
          } />
          <Route path="/signin" element={
            user ? <Navigate to="/shop" /> : <SignIn onLogin={login} />
          } />
          <Route path="/cart" element={
            user ? <Cart token={token} /> : <Navigate to="/signin" />
          } />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
