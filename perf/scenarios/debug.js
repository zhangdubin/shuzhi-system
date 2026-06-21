import http from 'k6/http';
import { check } from 'k6';
export const options = { vus: 1, iterations: 3 };
export default function () {
  const login = http.post('http://host.docker.internal:8000/api/v1/auth/login', JSON.stringify({account:'admin',password:'admin123'}), { headers: { 'Content-Type': 'application/json' } });
  const token = JSON.parse(login.body).token;
  const list = http.post('http://host.docker.internal:8000/api/v1/contracts/list', JSON.stringify({page:1,pageSize:1}), { headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } });
  const listData = JSON.parse(list.body);
  const item = listData.data.list[0];
  console.log('id:', item.id, 'contractId:', item.contractId, 'id||contractId:', item.id || item.contractId);
  const idKey = 'contractId';
  const id = item.id || item.contractId;
  const url = `http://host.docker.internal:8000/api/v1/contracts/detail?${idKey}=${id}`;
  const res = http.post(url, null, { headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } });
  console.log('detail url:', url, 'status:', res.status, 'body first 100:', res.body.substring(0, 100));
}
