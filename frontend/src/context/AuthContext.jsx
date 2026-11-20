import { createContext, useContext, useState } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    return localStorage.getItem('clarityRxUser') || 'Doctor';
  });

  const loginUser = (username) => {
    const val = username || 'Doctor';
    localStorage.setItem('clarityRxUser', val);
    setUser(val);
  };

  const logoutUser = () => {
    localStorage.removeItem('clarityRxUser');
    setUser('Doctor');
  };

  return (
    <AuthContext.Provider value={{ user, loginUser, logoutUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
