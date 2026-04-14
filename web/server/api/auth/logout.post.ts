import { success } from '~~/server/utils/response'

export default defineEventHandler(async () => {
  // JWT is stateless — client discards the token.
  // If refresh token revocation is needed later, add a blocklist table.
  return success({ loggedOut: true })
})
