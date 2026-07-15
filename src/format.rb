# frozen_string_literal: true

require 'json'
require 'anystyle'

# Gets output from Python
def main
  input = $stdin.read

  begin
    references = JSON.parse(input)
  rescue JSON::ParserError
    warn "Invalid JSON received, references can't be parsed"
    exit 1
  end

  format(references)
end

# Parses all references and sends back to Python
def format(references)
  output = []

  references.each do |ref|
    result = AnyStyle.parse(ref)
    output << result if result
  end

  puts output.to_json
end

main if __FILE__ == $PROGRAM_NAME
