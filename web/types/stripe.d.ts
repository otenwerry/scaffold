declare global {
  namespace JSX {
    interface IntrinsicElements {
      'stripe-pricing-table': {
        'pricing-table-id': string;
        'publishable-key': string;
        children?: React.ReactNode;
      };
    }
  }
}

export {};
