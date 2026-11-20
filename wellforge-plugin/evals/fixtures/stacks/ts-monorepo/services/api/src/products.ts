import { Hono } from "hono";

export const products = new Hono();
products.get("/", (c) => c.json([{ id: 1, name: "Mug" }]));
