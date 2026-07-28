# Lumo → Startify: push catalog webhook

When Lumo monitoring + LLM classifies a new contest, Lumo **automatically POSTs** it to Startify.
Startify upserts the card on the site — no manual copy-paste.

---

## Flow

```
Telegram channels
      ↓
Lumo monitor + LLM → catalog_opportunities
      ↓
POST STARTIFY_CATALOG_WEBHOOK_URL   (event: opportunity.created)
      ↓
Startify NestJS → Prisma → карточки на сайте
```

**Fallback (full sync):** Startify can still poll `GET /api/partner/v1/catalog/opportunities` on a cron.
Push is faster — new contests appear on the site within seconds.

---

## Lumo Railway env

```env
PARTNER_API_KEY=<same Bearer as Startify>
STARTIFY_CATALOG_WEBHOOK_URL=https://api.aistartify.com/api/webhooks/lumo/catalog
STARTIFY_CATALOG_PUSH_ENABLED=true
```

Dev webhook: `https://api-dev.aistartify.com/api/webhooks/lumo/catalog`

See also [STARTIFY_INTEGRATION_CHECKLIST.md](./STARTIFY_INTEGRATION_CHECKLIST.md).

| Variable | Required | Description |
|----------|----------|-------------|
| `STARTIFY_CATALOG_WEBHOOK_URL` | Yes | Startify endpoint that receives pushes |
| `PARTNER_API_KEY` | Yes | Same secret on both sides (`Authorization: Bearer …`) |
| `STARTIFY_CATALOG_PUSH_ENABLED` | No | Default `true`; set `false` to pause pushes |

---

## Startify env

```env
LUMO_PARTNER_API_KEY=lumo_partner_I_xakIY1cpbkT_UNYar6yyHa0i-CBN40WpAo_Z9ALBE
```

Use the **same** key to verify incoming webhooks from Lumo.

---

## Webhook contract

### Request

```http
POST /api/webhooks/lumo/catalog
Authorization: Bearer <LUMO_PARTNER_API_KEY>
Content-Type: application/json
```

```json
{
  "event": "opportunity.created",
  "sentAt": "2026-06-29T18:00:00+00:00",
  "source": "lumo",
  "opportunity": {
    "id": 1234,
    "type": "конкурс",
    "emoji": "🏆",
    "label": "Конкурс",
    "tags": [{"type": "конкурс", "emoji": "🏆", "label": "Конкурс", "custom": false}],
    "title": "Название конкурса",
    "description": "Краткое описание",
    "deadline": "15.07.2026",
    "country": "Казахстан",
    "sourceChannelName": "Startup Channel",
    "requirements": "9–11 класс",
    "applicationUrl": "https://example.com/apply",
    "messageLink": "https://t.me/channel/123",
    "isPremium": true,
    "isActive": true
  }
}
```

### Events

| event | When |
|-------|------|
| `opportunity.created` | New active entry after LLM classification |
| `opportunity.updated` | Backfill script or manual re-push |
| `opportunity.deactivated` | Reserved for future (expired / removed) |

### Response

Return **HTTP 2xx** on success. Lumo retries up to 3 times on failure.

```json
{ "ok": true }
```

### Idempotency

Upsert by **`opportunity.id`** (Lumo catalog ID). Same ID → update card, do not duplicate.

---

## NestJS — reference implementation

### Prisma (`schema.prisma`)

```prisma
model LumoOpportunity {
  lumoId            Int      @unique
  type              String
  title             String
  description       String   @db.Text
  deadline          String
  requirements      String?  @db.Text
  applicationUrl    String?
  messageLink       String?
  sourceChannelName String?
  emoji             String?
  label             String?
  tags              Json?
  isPremium         Boolean  @default(false)
  isActive          Boolean  @default(true)
  rawPayload        Json
  syncedAt          DateTime @updatedAt
  createdAt         DateTime @default(now())

  @@index([isActive])
  @@index([deadline])
}
```

### Guard (`lumo-webhook.guard.ts`)

```typescript
import { CanActivate, ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';

@Injectable()
export class LumoWebhookGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const req = context.switchToHttp().getRequest();
    const auth = String(req.headers.authorization ?? '');
    const expected = process.env.LUMO_PARTNER_API_KEY ?? '';
    if (!expected || auth !== `Bearer ${expected}`) {
      throw new UnauthorizedException('Invalid Lumo webhook token');
    }
    return true;
  }
}
```

### DTO (`catalog-webhook.dto.ts`)

```typescript
import { IsIn, IsObject, IsString } from 'class-validator';

export class LumoCatalogWebhookDto {
  @IsIn(['opportunity.created', 'opportunity.updated', 'opportunity.deactivated'])
  event!: string;

  @IsString()
  sentAt!: string;

  @IsString()
  source!: string;

  @IsObject()
  opportunity!: Record<string, unknown>;
}
```

### Service (`catalog-sync.service.ts`)

```typescript
import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class CatalogSyncService {
  constructor(private prisma: PrismaService) {}

  async upsertFromWebhook(dto: { event: string; opportunity: any }) {
    const o = dto.opportunity;
    const isActive =
      dto.event === 'opportunity.deactivated'
        ? false
        : Boolean(o.isActive ?? true);

    return this.prisma.lumoOpportunity.upsert({
      where: { lumoId: Number(o.id) },
      create: {
        lumoId: Number(o.id),
        type: String(o.type ?? ''),
        title: String(o.title ?? ''),
        description: String(o.description ?? ''),
        deadline: String(o.deadline ?? 'не указан'),
        requirements: o.requirements ? String(o.requirements) : null,
        applicationUrl: o.applicationUrl ? String(o.applicationUrl) : null,
        messageLink: o.messageLink ? String(o.messageLink) : null,
        sourceChannelName: o.sourceChannelName ? String(o.sourceChannelName) : null,
        emoji: o.emoji ? String(o.emoji) : null,
        label: o.label ? String(o.label) : null,
        tags: o.tags ?? [],
        isPremium: Boolean(o.isPremium),
        isActive,
        rawPayload: o,
      },
      update: {
        type: String(o.type ?? ''),
        title: String(o.title ?? ''),
        description: String(o.description ?? ''),
        deadline: String(o.deadline ?? 'не указан'),
        requirements: o.requirements ? String(o.requirements) : null,
        applicationUrl: o.applicationUrl ? String(o.applicationUrl) : null,
        messageLink: o.messageLink ? String(o.messageLink) : null,
        sourceChannelName: o.sourceChannelName ? String(o.sourceChannelName) : null,
        emoji: o.emoji ? String(o.emoji) : null,
        label: o.label ? String(o.label) : null,
        tags: o.tags ?? [],
        isPremium: Boolean(o.isPremium),
        isActive,
        rawPayload: o,
      },
    });
  }
}
```

### Controller (`catalog-webhook.controller.ts`)

```typescript
import { Body, Controller, Post, UseGuards } from '@nestjs/common';
import { LumoWebhookGuard } from './lumo-webhook.guard';
import { LumoCatalogWebhookDto } from './catalog-webhook.dto';
import { CatalogSyncService } from './catalog-sync.service';

@Controller('api/webhooks/lumo')
@UseGuards(LumoWebhookGuard)
export class CatalogWebhookController {
  constructor(private catalog: CatalogSyncService) {}

  @Post('catalog')
  async onCatalogEvent(@Body() body: LumoCatalogWebhookDto) {
    await this.catalog.upsertFromWebhook(body);
    return { ok: true };
  }
}
```

### Next.js — list cards

```typescript
// app/grants/page.tsx — server component
const rows = await prisma.lumoOpportunity.findMany({
  where: { isActive: true },
  orderBy: { syncedAt: 'desc' },
});
```

---

## Manual tools (Lumo admin)

| Action | Command |
|--------|---------|
| Push one card | `/push_startify 1234` |
| Push all active | `/push_startify` |
| Backfill from CLI | `python scripts/push_catalog_to_startify.py` |

---

## Smoke test

```bash
# Startify must expose the endpoint first, then from Lumo machine:
export PARTNER_API_KEY=lumo_partner_I_xakIY1cpbkT_UNYar6yyHa0i-CBN40WpAo_Z9ALBE
export STARTIFY_CATALOG_WEBHOOK_URL=https://api.startify.example/api/webhooks/lumo/catalog

curl -s -X POST "$STARTIFY_CATALOG_WEBHOOK_URL" \
  -H "Authorization: Bearer $PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "opportunity.created",
    "sentAt": "2026-06-29T12:00:00+00:00",
    "source": "lumo",
    "opportunity": {
      "id": 999999,
      "type": "конкурс",
      "emoji": "🏆",
      "label": "Конкурс",
      "tags": [],
      "title": "Smoke test",
      "description": "Test from Lumo",
      "deadline": "не указан",
      "sourceChannelName": "Test",
      "requirements": null,
      "applicationUrl": null,
      "messageLink": "https://t.me/test/1",
      "isPremium": false,
      "isActive": true
    }
  }'
```

---

## Related docs

- [STARTIFY_API.md](./STARTIFY_API.md) — pull sync `GET /catalog/opportunities`
- [STARTIFY_CLAUDE_DEPLOY_PROMPT.md](./STARTIFY_CLAUDE_DEPLOY_PROMPT.md) — full Startify deploy prompt
