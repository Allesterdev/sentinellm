/**
 * SentineLLM OpenClaw Plugin
 *
 * Security middleware for OpenClaw that validates messages through SentineLLM API
 * to detect prompt injections and secret leakage.
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import axiosRetry from 'axios-retry';

/**
 * Configuration for SentineLLM plugin
 */
export interface SentineLLMConfig {
  /** SentineLLM API base URL */
  apiUrl: string;
  /** API key for authentication (optional) */
  apiKey?: string;
  /** Timeout in milliseconds (default: 5000) */
  timeout?: number;
  /** Maximum retry attempts (default: 3) */
  maxRetries?: number;
  /** Enable detailed validation response (default: false) */
  includeDetails?: boolean;
  /** Block on validation errors (default: true) */
  blockOnError?: boolean;
  /** Custom error message when blocked */
  blockedMessage?: string;
}

/**
 * Validation response from SentineLLM API
 */
export interface ValidationResponse {
  safe: boolean;
  blocked: boolean;
  threat_level: 'none' | 'low' | 'medium' | 'high';
  reason?: string;
  layers?: {
    secret_detection?: {
      detected: boolean;
      threat_level: string;
      secrets_found: number;
    };
    prompt_injection?: {
      detected: boolean;
      threat_level: string;
      confidence: number;
    };
    llm_detection?: {
      detected: boolean;
      threat_level: string;
      confidence: number;
    };
    entropy?: {
      detected: boolean;
      threat_level: string;
    };
  };
}

/**
 * Internal config with all required fields
 */
interface InternalConfig {
  apiUrl: string;
  apiKey?: string;
  timeout: number;
  maxRetries: number;
  includeDetails: boolean;
  blockOnError: boolean;
  blockedMessage: string;
}

/**
 * SentineLLM Plugin for OpenClaw
 */
export class SentineLLMPlugin {
  private client: AxiosInstance;
  private config: InternalConfig;

  constructor(config: SentineLLMConfig) {
    this.config = {
      timeout: 5000,
      maxRetries: 3,
      includeDetails: false,
      blockOnError: true,
      blockedMessage: '⛔ Message blocked by security policy',
      ...config,
    };

    // Create axios client with retry logic
    this.client = axios.create({
      baseURL: this.config.apiUrl,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
        ...(this.config.apiKey && { 'X-API-Key': this.config.apiKey }),
      },
    });

    // Configure retry strategy
    axiosRetry(this.client, {
      retries: this.config.maxRetries,
      retryDelay: axiosRetry.exponentialDelay,
      retryCondition: (error: AxiosError) => {
        return axiosRetry.isNetworkOrIdempotentRequestError(error) ||
          error.response?.status === 429;
      },
    });
  }

  /**
   * Validate a message through SentineLLM API
   */
  async validate(text: string): Promise<ValidationResponse> {
    try {
      const response = await this.client.post<ValidationResponse>(
        '/api/v1/validate',
        {
          text,
          include_details: this.config.includeDetails,
        }
      );

      return response.data;
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 403) {
          // Message was blocked
          return error.response.data as ValidationResponse;
        }
        // eslint-disable-next-line no-console
        console.error('SentineLLM API error:', error.message);
      }

      // If blockOnError is false, allow the message
      if (!this.config.blockOnError) {
        return {
          safe: true,
          blocked: false,
          threat_level: 'none',
        };
      }

      throw error;
    }
  }

  /**
   * Check API health status
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.client.get('/api/v1/health');
      return response.status === 200;
    } catch {
      return false;
    }
  }

  /**
   * OpenClaw hook: Validate inbound messages (user → AI)
   */
  async onInboundMessage(message: string): Promise<string> {
    const result = await this.validate(message);

    if (result.blocked) {
      throw new Error(this.config.blockedMessage + (result.reason ? `: ${result.reason}` : ''));
    }

    return message;
  }

  /**
   * OpenClaw hook: Validate outbound messages (AI → user)
   */
  async onOutboundMessage(message: string): Promise<string> {
    const result = await this.validate(message);

    if (result.blocked) {
      // Replace blocked content with safe message
      return this.config.blockedMessage + (result.reason ? `: ${result.reason}` : '');
    }

    return message;
  }

  /**
   * Batch validation for multiple messages
   */
  async validateBatch(messages: string[]): Promise<ValidationResponse[]> {
    try {
      const response = await this.client.post<ValidationResponse[]>(
        '/api/v1/validate/batch',
        messages.map(text => ({ text }))
      );

      return response.data;
    } catch (error: unknown) {
      // eslint-disable-next-line no-console
      console.error('SentineLLM batch validation error:', error);
      throw error;
    }
  }
}

/**
 * Factory function to create plugin instance
 */
export function createSentineLLMPlugin(config: SentineLLMConfig): SentineLLMPlugin {
  return new SentineLLMPlugin(config);
}

// Export types
export default SentineLLMPlugin;
