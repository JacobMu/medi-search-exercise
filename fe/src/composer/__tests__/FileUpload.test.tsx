import { FileUpload } from "@/composer/components/FileUpload";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

beforeEach(() => {
  global.URL.createObjectURL = jest.fn(() => "blob:mock-url");
  global.URL.revokeObjectURL = jest.fn();
});

describe("FileUpload", () => {
  it("renders label text", () => {
    render(<FileUpload label="Avatar Image" value={null} onChange={jest.fn()} />);
    expect(screen.getByText("Avatar Image")).toBeInTheDocument();
  });

  it("file input has default accept attribute", () => {
    render(<FileUpload label="Test" value={null} onChange={jest.fn()} />);
    const input = document.querySelector("input[type=file]") as HTMLInputElement;
    expect(input.accept).toBe("image/png,image/jpeg,image/webp");
  });

  it("custom accept attribute is forwarded to input", () => {
    render(<FileUpload label="Test" accept="image/png" value={null} onChange={jest.fn()} />);
    const input = document.querySelector("input[type=file]") as HTMLInputElement;
    expect(input.accept).toBe("image/png");
  });

  it("selecting a file calls onChange with the file", async () => {
    const onChange = jest.fn();
    render(<FileUpload label="Test" value={null} onChange={onChange} />);
    const input = document.querySelector("input[type=file]") as HTMLInputElement;
    const file = new File(["content"], "test.png", { type: "image/png" });
    await userEvent.upload(input, file);
    expect(onChange).toHaveBeenCalledWith(file);
  });

  it("shows preview img when value is a File", () => {
    const file = new File(["content"], "test.png", { type: "image/png" });
    render(<FileUpload label="Test" value={file} onChange={jest.fn()} />);
    expect(screen.getByRole("img")).toBeInTheDocument();
  });

  it("rejects files with disallowed MIME types", async () => {
    const onChange = jest.fn();
    render(<FileUpload label="Test" value={null} onChange={onChange} />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const badFile = new File(["content"], "malware.exe", {
      type: "application/octet-stream",
    });
    await userEvent.upload(input, badFile);
    expect(onChange).not.toHaveBeenCalledWith(expect.any(File));
  });
});
