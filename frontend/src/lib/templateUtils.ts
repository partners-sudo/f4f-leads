// Utility functions for template variable replacement

export interface TemplateVariables {
  name?: string
  company?: string
  email?: string
  [key: string]: string | undefined
}

/**
 * Replaces template variables (e.g., {{name}}, {{company}}) with actual values
 * @param template - The template string with variables
 * @param variables - Object containing variable values
 * @returns Template string with variables replaced
 */
export function replaceTemplateVariables(
  template: string,
  variables: TemplateVariables
): string {
  let result = template
  
  // Replace all variables in the format {{variableName}}
  Object.keys(variables).forEach((key) => {
    const value = variables[key] || ''
    const regex = new RegExp(`\\{\\{${key}\\}\\}`, 'g')
    result = result.replace(regex, value)
  })
  
  return result
}

/**
 * Extracts variable names from a template string
 * @param template - The template string
 * @returns Array of variable names found in the template
 */
export function extractVariables(template: string): string[] {
  const regex = /\{\{(\w+)\}\}/g
  const matches = template.matchAll(regex)
  const variables: string[] = []
  
  for (const match of matches) {
    if (!variables.includes(match[1])) {
      variables.push(match[1])
    }
  }
  
  return variables
}

