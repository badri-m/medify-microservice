import React, { useMemo, useState } from "react";
import axios from "axios";

const defaultBaseUrl = "/api";

function pretty(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export default function App() {
  const baseUrl = useMemo(() => {
    return (import.meta.env.VITE_ORDER_SERVICE_URL || defaultBaseUrl).replace(
      /\/+$/,
      "",
    );
  }, []);

  const [userName, setUserName] = useState("");
  const [userEmail, setUserEmail] = useState("");
  const [createdUserId, setCreatedUserId] = useState("");

  const [orderUserId, setOrderUserId] = useState("");
  const [orderSku, setOrderSku] = useState("ABC");
  const [orderQty, setOrderQty] = useState(1);
  const [orderTotal, setOrderTotal] = useState(19.99);

  const [lastOk, setLastOk] = useState("");
  const [lastErr, setLastErr] = useState("");

  async function createUser() {
    setLastOk("");
    setLastErr("");
    try {
      const resp = await axios.post(`${baseUrl}/users`, {
        name: userName,
        email: userEmail,
      });
      setCreatedUserId(resp.data.id);
      setOrderUserId(resp.data.id);
      setLastOk(pretty(resp.data));
    } catch (e) {
      setLastErr(pretty(e?.response?.data || e.message));
    }
  }

  async function createOrder() {
    setLastOk("");
    setLastErr("");
    try {
      const resp = await axios.post(`${baseUrl}/orders`, {
        user_id: orderUserId,
        items: [{ sku: orderSku, qty: Number(orderQty) }],
        total: Number(orderTotal),
      });
      setLastOk(pretty(resp.data));
    } catch (e) {
      setLastErr(pretty(e?.response?.data || e.message));
    }
  }

  async function listOrders() {
    setLastOk("");
    setLastErr("");
    try {
      const resp = await axios.get(`${baseUrl}/orders`);
      setLastOk(pretty(resp.data));
    } catch (e) {
      setLastErr(pretty(e?.response?.data || e.message));
    }
  }

  return (
    <div
      style={{
        fontFamily: "system-ui, Segoe UI, Arial",
        padding: 24,
        maxWidth: 900,
        margin: "0 auto",
      }}
    >
      <h2>Microservices Demo</h2>
      <p style={{ color: "#444" }}>
        Frontend talks only to <b>order-service</b> at <code>{baseUrl}</code>.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <section
          style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16 }}
        >
          <h3>Create User</h3>
          <label style={{ display: "block", marginBottom: 8 }}>
            Name
            <input
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              style={{ width: "100%" }}
            />
          </label>
          <label style={{ display: "block", marginBottom: 8 }}>
            Email
            <input
              value={userEmail}
              onChange={(e) => setUserEmail(e.target.value)}
              style={{ width: "100%" }}
            />
          </label>
          <button onClick={createUser} style={{ padding: "8px 12px" }}>
            Create User
          </button>
          {createdUserId ? (
            <p style={{ marginTop: 10, color: "#0a6" }}>
              Created user id: <code>{createdUserId}</code>
            </p>
          ) : null}
        </section>

        <section
          style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16 }}
        >
          <h3>Create Order</h3>
          <label style={{ display: "block", marginBottom: 8 }}>
            User ID
            <input
              value={orderUserId}
              onChange={(e) => setOrderUserId(e.target.value)}
              style={{ width: "100%" }}
            />
          </label>
          <label style={{ display: "block", marginBottom: 8 }}>
            SKU
            <input
              value={orderSku}
              onChange={(e) => setOrderSku(e.target.value)}
              style={{ width: "100%" }}
            />
          </label>
          <label style={{ display: "block", marginBottom: 8 }}>
            Qty
            <input
              type="number"
              value={orderQty}
              onChange={(e) => setOrderQty(e.target.value)}
              style={{ width: "100%" }}
            />
          </label>
          <label style={{ display: "block", marginBottom: 8 }}>
            Total
            <input
              type="number"
              step="0.01"
              value={orderTotal}
              onChange={(e) => setOrderTotal(e.target.value)}
              style={{ width: "100%" }}
            />
          </label>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={createOrder} style={{ padding: "8px 12px" }}>
              Create Order
            </button>
            <button onClick={listOrders} style={{ padding: "8px 12px" }}>
              List Orders
            </button>
          </div>
          <p style={{ marginTop: 10, color: "#666", fontSize: 13 }}>
            Order creation triggers: frontend → order-service → user-service →
            user-db.
          </p>
        </section>
      </div>

      <section
        style={{
          marginTop: 16,
          border: "1px solid #ddd",
          borderRadius: 8,
          padding: 16,
        }}
      >
        <h3>Response</h3>
        {lastOk ? (
          <pre
            style={{
              background: "#f7f7f7",
              padding: 12,
              borderRadius: 6,
              overflowX: "auto",
            }}
          >
            {lastOk}
          </pre>
        ) : null}
        {lastErr ? (
          <pre
            style={{
              background: "#fff0f0",
              padding: 12,
              borderRadius: 6,
              overflowX: "auto",
            }}
          >
            {lastErr}
          </pre>
        ) : null}
      </section>
    </div>
  );
}
