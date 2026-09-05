import bcrypt from "bcryptjs";
import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { conflict } from "../errors.js";
import { authenticate } from "../plugins/auth.js";

const registerSchema = z.object({
  email: z.email().transform((value) => value.toLowerCase()),
  password: z.string().min(10).max(128),
  displayName: z.string().trim().min(2).max(80),
});

const loginSchema = z.object({
  email: z.email().transform((value) => value.toLowerCase()),
  password: z.string().min(1).max(128),
});

interface UserRow {
  id: string;
  email: string;
  password_hash: string;
  display_name: string;
  onboarding_completed_at: Date | null;
}

function publicUser(user: UserRow) {
  return {
    id: user.id,
    email: user.email,
    displayName: user.display_name,
    onboardingComplete: user.onboarding_completed_at !== null,
  };
}

export async function authRoutes(app: FastifyInstance): Promise<void> {
  app.post("/register", async (request, reply) => {
    const body = registerSchema.parse(request.body);
    const passwordHash = await bcrypt.hash(body.password, 12);
    if (app.demo) {
      const user = app.demo.createUser(body.email, passwordHash, body.displayName);
      const accessToken = await reply.jwtSign({ sub: user.id, email: user.email });
      return reply.code(201).send({ accessToken, user: publicUser(user) });
    }
    try {
      const result = await app.db.query<UserRow>(
        `INSERT INTO users (email, password_hash, display_name)
         VALUES ($1, $2, $3)
         RETURNING id, email::text, password_hash, display_name, onboarding_completed_at`,
        [body.email, passwordHash, body.displayName],
      );
      const user = result.rows[0];
      if (!user) throw new Error("User insert returned no row");
      const accessToken = await reply.jwtSign({ sub: user.id, email: user.email });
      return reply.code(201).send({ accessToken, user: publicUser(user) });
    } catch (error) {
      if (typeof error === "object" && error !== null && "code" in error && error.code === "23505") {
        throw conflict("EMAIL_TAKEN", "An account already exists for this email");
      }
      throw error;
    }
  });

  app.post("/login", async (request, reply) => {
    const body = loginSchema.parse(request.body);
    if (app.demo) {
      const user = app.demo.findUserByEmail(body.email);
      if (!user || !(await app.demo.passwordMatches(user, body.password))) {
        return reply.code(401).send({ error: "INVALID_CREDENTIALS", message: "Invalid email or password" });
      }
      const accessToken = await reply.jwtSign({ sub: user.id, email: user.email });
      return { accessToken, user: publicUser(user) };
    }
    const result = await app.db.query<UserRow>(
      `SELECT id, email::text, password_hash, display_name, onboarding_completed_at
       FROM users WHERE email = $1`,
      [body.email],
    );
    const user = result.rows[0];
    if (!user || !(await bcrypt.compare(body.password, user.password_hash))) {
      return reply.code(401).send({ error: "INVALID_CREDENTIALS", message: "Invalid email or password" });
    }
    const accessToken = await reply.jwtSign({ sub: user.id, email: user.email });
    return { accessToken, user: publicUser(user) };
  });

  app.get("/me", { preHandler: authenticate }, async (request) => {
    if (app.demo) {
      const user = app.demo.getUser(request.user.sub);
      return { user: user ? publicUser(user) : null };
    }
    const result = await app.db.query<UserRow>(
      `SELECT id, email::text, password_hash, display_name, onboarding_completed_at
       FROM users WHERE id = $1`,
      [request.user.sub],
    );
    const user = result.rows[0];
    return { user: user ? publicUser(user) : null };
  });
}
