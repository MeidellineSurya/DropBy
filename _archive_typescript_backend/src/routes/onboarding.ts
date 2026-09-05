import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { authenticate } from "../plugins/auth.js";

const onboardingSchema = z.object({
  displayName: z.string().trim().min(2).max(80),
  birthDate: z.iso.date().optional(),
  interestTags: z.array(z.string().trim().min(1).max(40)).max(20).default([]),
  vibeTags: z.array(z.string().trim().min(1).max(40)).max(10).default([]),
  locationPermission: z.enum(["denied", "while_using", "always"]),
});

export async function onboardingRoutes(app: FastifyInstance): Promise<void> {
  app.put("/", { preHandler: authenticate }, async (request) => {
    const body = onboardingSchema.parse(request.body);
    if (app.demo) {
      const user = app.demo.completeOnboarding(request.user.sub, body.displayName);
      return {
        user: {
          id: user.id,
          displayName: user.display_name,
          birthDate: body.birthDate ?? null,
          interestTags: body.interestTags,
          vibeTags: body.vibeTags,
          locationPermission: body.locationPermission,
          onboardingCompletedAt: user.onboarding_completed_at?.toISOString(),
        },
      };
    }
    const result = await app.db.query<{
      id: string;
      display_name: string;
      birth_date: string | null;
      interest_tags: string[];
      vibe_tags: string[];
      location_permission: string;
      onboarding_completed_at: Date;
    }>(
      `UPDATE users SET
         display_name = $2,
         birth_date = $3,
         interest_tags = $4,
         vibe_tags = $5,
         location_permission = $6,
         onboarding_completed_at = now(),
         updated_at = now()
       WHERE id = $1
       RETURNING id, display_name, birth_date::text, interest_tags, vibe_tags,
                 location_permission, onboarding_completed_at`,
      [request.user.sub, body.displayName, body.birthDate ?? null, body.interestTags, body.vibeTags, body.locationPermission],
    );
    const user = result.rows[0];
    return {
      user: user && {
        id: user.id,
        displayName: user.display_name,
        birthDate: user.birth_date,
        interestTags: user.interest_tags,
        vibeTags: user.vibe_tags,
        locationPermission: user.location_permission,
        onboardingCompletedAt: user.onboarding_completed_at.toISOString(),
      },
    };
  });
}
