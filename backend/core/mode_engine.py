"""
SELENE OS — Mode Engine
Selects the operating mode (GLOBAL / HYBRID / PERSONAL) based on intent and context.

Phase 0-1: Deterministic mapping from intent
Phase 2+:  Latent space user modeling with DEP embeddings
"""

from schemas import IntentResult, ModeType
import structlog

logger = structlog.get_logger(__name__)


# ── Mode-Specific System Prompt Augmentations ────────────────────

MODE_PROMPTS = {
    ModeType.GLOBAL: """
Operating in GLOBAL mode.
- Prioritize factual accuracy and objectivity
- Use structured, formal language
- Cite sources when possible
- Avoid speculation or subjective commentary
- Focus on deterministic, verifiable information
""",
    ModeType.HYBRID: """
Operating in HYBRID mode.
- Balance factual accuracy with conversational warmth
- Adapt tone based on the query complexity
- Provide context-aware suggestions
- Be helpful and approachable while maintaining precision
""",
    ModeType.PERSONAL: """
Operating in PERSONAL mode.
- Deeply personalized responses adapted to the user's style
- Proactive suggestions based on user patterns
- Creative and expressive when appropriate
- Anticipate user needs and preferences
- Use a conversational, tailored communication style
""",
}


import numpy as np

class SparseAutoencoderFilter:
    """
    Sparse Autoencoder (SAE) filter to extract and align latent personalization features.
    Projects DEP embeddings onto sparse dictionary directions representing user preferences.
    """
    def __init__(self, input_dim: int = 1536, hidden_dim: int = 256):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        # Deterministic weights using pseudo-random seed to make it reproducible and zero-dependency
        rng = np.random.default_rng(42)
        # Encoder weights (W_enc) and bias (b_enc)
        self.W_enc = rng.normal(0.0, 1.0 / np.sqrt(input_dim), (hidden_dim, input_dim))
        self.b_enc = rng.normal(0.0, 0.01, (hidden_dim,))
        # Decoder weights (W_dec) and bias (b_dec)
        self.W_dec = rng.normal(0.0, 1.0 / np.sqrt(hidden_dim), (input_dim, hidden_dim))
        self.b_dec = rng.normal(0.0, 0.01, (input_dim,))

    def encode(self, x: np.ndarray) -> np.ndarray:
        # Activating with ReLU to induce sparsity
        h = np.dot(self.W_enc, x) + self.b_enc
        # Sparsification thresholding (keep top 10% activations or threshold > 0)
        h = np.maximum(0, h)
        # Induce higher sparsity: zero out values below the median
        median = np.median(h)
        h[h < median] = 0.0
        return h

    def decode(self, h: np.ndarray) -> np.ndarray:
        return np.dot(self.W_dec, h) + self.b_dec

    def reconstruct_and_align(self, x: np.ndarray) -> np.ndarray:
        """Runs the autoencoder pass to filter and align the preferences."""
        h = self.encode(x)
        reconstructed = self.decode(h)
        # Normalize reconstructed vector
        norm = np.linalg.norm(reconstructed)
        if norm > 0:
            reconstructed = reconstructed / norm
        return reconstructed


class DEPEngine:
    """
    Difference-aware Embedding-based Personalization (DEP) Engine.
    Computes difference between a standard baseline profile embedding and the user's specific embedding.
    """
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self.sae = SparseAutoencoderFilter(input_dim=dimension)

    def compute_delta(self, base_embedding: list[float], user_embedding: list[float]) -> list[float]:
        """Calculates delta vector between base and user profile embeddings."""
        v_base = np.array(base_embedding)
        v_user = np.array(user_embedding)
        # Difference-aware delta
        delta = v_user - v_base
        # Pass through the sparse autoencoder to filter out noise / align preference signals
        aligned_delta = self.sae.reconstruct_and_align(delta)
        return aligned_delta.tolist()


dep_engine = DEPEngine()


def select_mode(intent_result: IntentResult, user_profile: dict = None) -> ModeType:
    """
    Determine the operating mode based on intent classification and user context.
    Incorporates user profile embeddings (DEP) and sparse autoencoder filtration.
    """
    mode = intent_result.mode
    personalization_strength = 0.0

    # DEPPersonalization check
    if user_profile and "user_embedding" in user_profile:
        # Standard system baseline embedding (e.g. neutral helper representation)
        base_embedding = user_profile.get("base_embedding", [0.0] * 1536)
        user_embedding = user_profile["user_embedding"]
        
        # Ensure dimensions match
        if len(base_embedding) == 1536 and len(user_embedding) == 1536:
            try:
                # Compute difference-aware personalization delta vector
                aligned_delta = dep_engine.compute_delta(base_embedding, user_embedding)
                personalization_strength = float(np.linalg.norm(aligned_delta))
                
                # If delta is strong, nudge mode towards PERSONAL
                if personalization_strength > 0.4 and intent_result.confidence < 0.9:
                    mode = ModeType.PERSONAL
            except Exception as e:
                logger.error("dep_personalization_failed", error=str(e))

    # User profile preferred_mode override
    if user_profile:
        preferred_mode = user_profile.get("preferred_mode")
        if preferred_mode:
            if isinstance(preferred_mode, str):
                try:
                    preferred_mode = ModeType(preferred_mode)
                except ValueError:
                    preferred_mode = None
            if isinstance(preferred_mode, ModeType) and intent_result.confidence < 0.8:
                mode = preferred_mode

    logger.info(
        "mode_selected",
        intent=intent_result.intent.value,
        mode=mode.value,
        confidence=intent_result.confidence,
        personalization_strength=f"{personalization_strength:.4f}"
    )

    return mode


def get_mode_prompt(mode: ModeType) -> str:
    """Get the system prompt augmentation for the selected mode."""
    return MODE_PROMPTS.get(mode, MODE_PROMPTS[ModeType.HYBRID])
