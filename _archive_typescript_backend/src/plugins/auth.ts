import type { FastifyInstance, FastifyRequest } from "fastify";
import fastifyJwt from "@fastify/jwt";

export async function registerAuth(app: FastifyInstance): Promise<void> {
  await app.register(fastifyJwt, {
    secret: app.config.JWT_SECRET,
    sign: { expiresIn: app.config.JWT_EXPIRES_IN },
  });
}

export async function authenticate(request: FastifyRequest): Promise<void> {
  await request.jwtVerify();
}
