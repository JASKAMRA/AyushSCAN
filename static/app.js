const form = document.getElementById('upload-form');
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const file = document.getElementById('bill-input').files[0];
  const formData = new FormData();
  formData.append('bill', file);

  const res = await fetch('http://localhost:5000/scan', {
    method: 'POST',
    body: formData
  });

  const data = await res.json();
  document.getElementById('result').innerText = data.result;
});
