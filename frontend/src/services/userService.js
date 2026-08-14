export async function getUsers() {
  const response = await fetch('/api/users');

  if (!response.ok) {
    throw new Error('No fue posible cargar los usuarios');
  }

  return response.json();
}
