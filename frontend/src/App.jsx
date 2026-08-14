import { useEffect, useState } from 'react';
import UserList from './components/UserList';
import { getUsers } from './services/userService';

function App() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getUsers()
      .then(setUsers)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="container">
      <section className="hero">
        <span className="badge">Base Full Stack</span>
        <h1>React + NestJS MVC</h1>
        <p>
          Frontend React conectado a un backend NestJS escrito en JavaScript.
        </p>
      </section>

      <section className="panel">
        <h2>Usuarios desde el backend</h2>
        {loading && <p>Cargando...</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && <UserList users={users} />}
      </section>
    </main>
  );
}

export default App;
