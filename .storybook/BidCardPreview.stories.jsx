import BidCardPreview from "../src/ui/components/BidCardPreview";

export default {
  title: "BidCardPreview",
  component: BidCardPreview,
};

const template = (args) => <BidCardPreview {...args} />;

export const Final = template.bind({});
Final.args = {
  card: {
    scope_json: { title: "Replace roof", description: "Need new shingles" },
    category: "repair",
    status: "final",
  },
};