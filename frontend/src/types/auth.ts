export interface CustomerUser {
  customer_id: number;
  name: string;
  email: string;
  is_verified: boolean;
}

export interface CustomerAuthData extends CustomerUser {
  access_token: string;
  token_type: string;
}
