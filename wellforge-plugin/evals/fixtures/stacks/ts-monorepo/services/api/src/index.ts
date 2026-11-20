import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { products } from "./products";

const app = new Hono();
app.route("/products", products);

serve({ fetch: app.fetch, port: 3000 });
export default app;
